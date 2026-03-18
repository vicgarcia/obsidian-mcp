'''
Obsidian MCP server with FastMCP tools.

Provides MCP tools for interacting with an Obsidian vault including
file operations, journal management, project organization, and wiki articles.
'''

import argparse
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from obsidian_mcp.schema import (
    FilePathInput,
    FileWriteInput,
    ProjectInput,
    YearMonthInput,
    create_error_response,
    create_success_response,
)
from obsidian_mcp.vault_client import VaultClient, VaultError

logger = logging.getLogger(__name__)

_HELP = '''
environment variables:
  OBSIDIAN_VAULT_PATH   Path to the Obsidian vault directory
  TZ                    Timezone for journal dates (e.g., America/New_York)
  LOG_LEVEL             Logging level (debug or info, default: info)
'''

# module-level client singleton
_client: Optional[VaultClient] = None


def parse_args() -> argparse.Namespace:
    '''Parse command line arguments.'''
    parser = argparse.ArgumentParser(
        prog='obsidian-mcp',
        description='Obsidian MCP server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_HELP
    )
    parser.add_argument(
        '--vault',
        default=os.getenv('OBSIDIAN_VAULT_PATH', '/vault'),
        metavar='PATH',
        help='path to Obsidian vault (or OBSIDIAN_VAULT_PATH env var)'
    )
    return parser.parse_args()


def get_client() -> VaultClient:
    '''Get the vault client singleton.'''
    if _client is None:
        raise RuntimeError('Vault client not initialized')
    return _client


def format_error(error: Exception) -> Dict[str, Any]:
    '''Format an exception as an error response.'''
    return create_error_response(str(error))


# mcp server

mcp = FastMCP('Obsidian MCP')


# file tools

@mcp.tool()
def read_file(file_path: str) -> Dict[str, Any]:
    '''
    Read file content from the Obsidian vault.

    Args:
        file_path: Vault-relative path to the file

    Returns:
        Dictionary with file content or error message
    '''
    try:
        logger.debug(f'read_file called with path: {file_path}')
        validated_input = FilePathInput(file_path=file_path)

        with get_client() as vault:
            content = vault.read_file(validated_input.file_path)
            return {'content': content}

    except ValidationError as e:
        logger.error(f'validation error reading file: {e}')
        return create_error_response(f'Invalid input: {e}')
    except VaultError as e:
        logger.error(f'vault error reading file: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error reading file: {e}')
        return create_error_response(f'Unexpected error reading file: {e}')


@mcp.tool()
def write_file(file_path: str, content: str) -> Dict[str, Any]:
    '''
    Write content to a file in the Obsidian vault.
    It's good practice to read from a file before writing to ensure nothing is overwritten.

    Args:
        file_path: Vault-relative path to the file
        content: Content to write to the file

    Returns:
        Dictionary with success indicator or error message
    '''
    try:
        logger.debug(f'write_file called with path: {file_path} ({len(content)} chars)')
        validated_input = FileWriteInput(file_path=file_path, content=content)

        with get_client() as vault:
            vault.write_file(validated_input.file_path, validated_input.content)
            return create_success_response()

    except ValidationError as e:
        logger.error(f'validation error writing file: {e}')
        return create_error_response(f'Invalid input: {e}')
    except VaultError as e:
        logger.error(f'vault error writing file: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error writing file: {e}')
        return create_error_response(f'Unexpected error writing file: {e}')


# date tools

@mcp.tool()
def get_current_date() -> Dict[str, str]:
    '''
    Get the current date in both human-readable and YYYY-MM-DD formats.

    Returns:
        Dictionary with date in YYYY-MM-DD format and human-readable format
    '''
    try:
        logger.debug('get_current_date called')
        now = datetime.now()
        formatted_date = now.strftime('%Y-%m-%d')
        human_date = now.strftime('%A %B %d, %Y')
        logger.info(f'current date: {formatted_date} ({human_date})')
        return {
            'formatted': formatted_date,
            'human': human_date
        }
    except Exception as e:
        logger.exception(f'unexpected error getting current date: {e}')
        return create_error_response(f'Unexpected error getting current date: {e}')


# journal tools

@mcp.tool()
def list_todays_journal_entry() -> Dict[str, Any]:
    '''
    Get today's journal entry path in the format journal/YYYY/MM/YYYY-MM-DD.md.

    A journal entry file will generally consist of a narritive diary for the day
    at the top, then a markdown horizontal rule of three dashes ---, then a section
    for freeform notes and text snippets from the day.

    When writing a daily journal entry, read the file first. When adding the entry
    for the day, place the narration at the top of the file and seperate from existing
    content with a horizontal rule if the file is not already formatted as such.

    Do not include a header with the date in the file, Obsidian handles this.

    Returns:
        Dictionary with today's journal entry path and name
    '''
    try:
        logger.debug('list_todays_journal_entry called')
        with get_client() as vault:
            journal_path = vault.get_journal_path()
            logger.info(f"today's journal path: {journal_path}")
            return {
                'path': journal_path,
                'name': Path(journal_path).name
            }
    except VaultError as e:
        logger.error(f'vault error getting journal entry: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error getting today\'s journal entry: {e}')
        return create_error_response(f'Unexpected error getting today\'s journal entry: {e}')


DAILY_NOTES_PROMPT = '''
you are assisting with a daily notes session, your role:

help capture the user's day through interactive note-taking.
be engaged and curious.
help them think deeper about their work.

session flow:

1. announce the date

announce that today is {today}.
ask if this is the correct date for this session.
assume that no response is confirmation of the date.
if they're catching up on a previous day or started after midnight, they should tell you the correct date.
remember this date for creating the journal entry later.

2. collect notes throughout the day

as the user shares updates:
- acknowledge what they shared
- ask 2-3 follow-up questions to help them elaborate
- focus on context, challenges, decisions, outcomes
- keep questions natural and conversational
- don't force responses, move on when they share next update
- accumulate context from everything shared

good follow-up questions probe:
- why they chose a particular approach
- what challenges or blockers they hit
- what they learned or would do differently
- how it connects to larger goals
- technical details worth remembering

3. generate the journal entry

when the user asks to update their journal
(e.g. "update my journal", "write today's entry", "save notes"):

use the session date from step 1.

check if entry exists:
- use list_todays_journal_entry() to get today's path
- if session date differs from today, construct path: journal/YYYY/MM/YYYY-MM-DD.md
- use read_file() to check existing content

create or update the entry:

format: narrative paragraphs, then --- separator, then freeform notes

narrative section:
- write 2-4 paragraphs in first person telling the story of the day
- synthesize everything discussed into coherent narrative
- focus on what was accomplished, challenges faced, decisions made, insights gained
- include specific technical details where relevant
- make it valuable to read months later
- natural personal voice, not a status report

separator: three dashes --- on their own line

freeform notes section:
- quick references, links, commands, snippets mentioned
- ideas or todos that came up
- anything worth preserving that doesn't fit narrative
- use bullet points, code blocks, whatever makes sense

if entry already exists:
- read it first
- preserve existing narrative, add to it rather than replace
- merge or append to freeform notes
- never include header with date, obsidian handles this

use write_file() with the journal path to save.

guidelines:

- be conversational and engaged
- remember everything for the final journal entry
- questions are optional prompts for deeper thinking
- synthesize everything into cohesive story
- make entries valuable months later
- focus on why and how, not just what
'''


@mcp.tool()
def start_daily_notes_session() -> str:
    '''
    Start a daily notes session to track the day's activities and progress.

    Initiates an interactive workflow that announces the date, collects notes with
    follow-up questions, and generates journal entries.

    Returns:
        Prompt instructions for the daily notes workflow
    '''
    now = datetime.now()
    today = now.strftime('%A %B %d, %Y')
    return DAILY_NOTES_PROMPT.format(today=today)


@mcp.tool()
def list_journal_entries_by_year_and_month(year: str, month: str) -> List[Dict[str, str]]:
    '''
    List all journal entries for a specific year and month.
    Journal entries are organized as journal/YYYY/MM/YYYY-MM-DD.md.

    Args:
        year: Year in YYYY format (e.g., "2025")
        month: Month in MM format with leading zero (e.g., "01" for January, "10" for October)

    Returns:
        List of journal entries with metadata
    '''
    try:
        logger.debug(f'list_journal_entries_by_year_and_month called: year={year}, month={month}')
        validated_input = YearMonthInput(year=year, month=month)

        with get_client() as vault:
            entries = vault.list_journal_entries(validated_input.year, validated_input.month)
            return entries

    except ValidationError as e:
        logger.error(f'validation error listing journal entries: {e}')
        return [create_error_response(f'Invalid input: {e}')]
    except VaultError as e:
        logger.error(f'vault error listing journal entries: {e}')
        return [format_error(e)]
    except Exception as e:
        logger.exception(f'unexpected error listing journal entries: {e}')
        return [create_error_response(f'Unexpected error listing journal entries: {e}')]


# project tools

@mcp.tool()
def list_projects() -> List[Dict[str, str]]:
    '''
    List all projects (subdirectories in the projects directory).

    Projects are simple directory-based organization for ongoing work. Use spaces in
    project names (e.g., "home automation", "blog redesign") and organize related
    documentation within each project directory.

    Returns:
        List of project directories with metadata
    '''
    try:
        logger.debug('list_projects called')
        with get_client() as vault:
            return vault.list_projects()
    except VaultError as e:
        logger.error(f'vault error listing projects: {e}')
        return [format_error(e)]
    except Exception as e:
        logger.exception(f'unexpected error listing projects: {e}')
        return [create_error_response(f'Unexpected error listing projects: {e}')]


@mcp.tool()
def list_project_content(project: str) -> List[Dict[str, str]]:
    '''
    List all files and directories within a project.

    Args:
        project: Name of the project directory

    Returns:
        List of files and directories with metadata
    '''
    try:
        logger.debug(f'list_project_content called: project={project}')
        validated_input = ProjectInput(project=project)

        with get_client() as vault:
            return vault.list_project_content(validated_input.project)

    except ValidationError as e:
        logger.error(f'validation error listing project content: {e}')
        return [create_error_response(f'Invalid input: {e}')]
    except VaultError as e:
        logger.error(f'vault error listing project content: {e}')
        return [format_error(e)]
    except Exception as e:
        logger.exception(f'unexpected error listing project content: {e}')
        return [create_error_response(f'Unexpected error listing project content: {e}')]


@mcp.tool()
def create_project(project: str) -> Dict[str, Any]:
    '''
    Create a new project directory.

    Args:
        project: Name of the project directory to create

    Returns:
        Success indicator or error message
    '''
    try:
        logger.debug(f'create_project called: project={project}')
        validated_input = ProjectInput(project=project)

        with get_client() as vault:
            vault.create_project(validated_input.project)
            return create_success_response()

    except ValidationError as e:
        logger.error(f'validation error creating project: {e}')
        return create_error_response(f'Invalid input: {e}')
    except VaultError as e:
        logger.error(f'vault error creating project: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error creating project: {e}')
        return create_error_response(f'Unexpected error creating project: {e}')


# wiki tools

@mcp.tool()
def list_wiki() -> List[Dict[str, str]]:
    '''
    List all wiki articles in the obsidian wiki.

    Wiki articles are comprehensive, standalone documentation on specific topics. Use
    descriptive filenames with spaces in lowercase (e.g., "python asyncio.md", "docker
    networking.md") in a flat directory structure for easy discovery.

    Returns:
        List of markdown files with metadata
    '''
    try:
        logger.debug('list_wiki called')
        with get_client() as vault:
            return vault.list_wiki()
    except VaultError as e:
        logger.error(f'vault error listing wiki: {e}')
        return [format_error(e)]
    except Exception as e:
        logger.exception(f'unexpected error listing wiki: {e}')
        return [create_error_response(f'Unexpected error listing wiki: {e}')]


# entry point

def run():
    '''Main entry point for the Obsidian MCP server.'''
    global _client

    logging.basicConfig(
        level=logging.DEBUG if os.getenv('LOG_LEVEL', 'info').lower() == 'debug' else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    args = parse_args()

    if not args.vault:
        logger.error('vault path is required (--vault or OBSIDIAN_VAULT_PATH env var)')
        raise SystemExit(1)

    logger.info('starting Obsidian MCP server')

    try:
        vault_path = Path(args.vault).resolve()
        logger.info(f'vault path configured: {vault_path}')

        if not vault_path.exists():
            logger.error(f'vault directory does not exist: {vault_path}')
            raise SystemExit(1)

        if not vault_path.is_dir():
            logger.error(f'vault path is not a directory: {vault_path}')
            raise SystemExit(1)

        # initialize client singleton
        _client = VaultClient(str(vault_path))

        mcp.run()

    except KeyboardInterrupt:
        logger.info('server shutdown requested')

    except Exception as e:
        logger.error(f'server error: {e}')
        raise SystemExit(1)


if __name__ == '__main__':
    run()
