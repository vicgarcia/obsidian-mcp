'''
Obsidian MCP server with FastMCP tools.

Provides MCP tools for interacting with an Obsidian vault including
file operations, journal management, project organization, and wiki articles.
'''

import argparse
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from obsidian_mcp.schema import (
    FilePathInput,
    FileWriteInput,
    JournalDateInput,
    JournalTextInput,
    JournalWriteInput,
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


# journal format guidance, sent to clients as the server instructions

JOURNAL_FORMAT = '''
journal files live at journal/YYYY/MM/YYYY-MM-DD.md, one file per day.

a day's file holds one or more entries. each entry:
- starts with a ### heading that names the entry (a short title, not the date)
- uses #### headings for sections within the entry and ##### for subsections
- never uses # or ## headings, and doesn't skip levels (no ##### directly under ###)
- is written in first person, natural voice, valuable to read months later
- keeps quick references (links, commands, snippets, todos) in a #### section inside the entry

never add a date heading or title to the file, obsidian handles this.

editing a journal file (date is YYYY-MM-DD, defaults to today):
- append_to_journal_entry adds text at the end of the file. start it with a ### heading
  to add a new entry; text without a heading continues the last entry.
- prepend_to_journal_entry adds text at the top of the file (after any yaml frontmatter).
  prepended text should always be a complete entry starting with a ### heading.
- write_journal_entry replaces the whole file. read the entry first with read_journal_entry
  and preserve existing entries; use this to edit or reorganize existing entries.
'''

# mcp server

mcp = FastMCP('Obsidian MCP', instructions=JOURNAL_FORMAT)


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
    For journal files, use write_journal_entry, append_to_journal_entry, or
    prepend_to_journal_entry instead.

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

def format_timestamp(now: datetime) -> Dict[str, Any]:
    '''Format a local datetime as every representation the timestamp tool returns.'''
    offset = now.utcoffset()
    if offset is None:
        utc_offset = ''
        utc = ''
    else:
        minutes = int(offset.total_seconds() // 60)
        sign = '+' if minutes >= 0 else '-'
        utc_offset = f'{sign}{abs(minutes) // 60:02d}:{abs(minutes) % 60:02d}'
        utc = now.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    time_12h = f'{now.hour % 12 or 12}:{now:%M %p}'
    human_date = f'{now:%A %B} {now.day}, {now.year}'
    iso_year, iso_week, _ = now.isocalendar()

    return {
        'iso': now.isoformat(timespec='seconds'),
        'utc': utc,
        'unix': int(now.timestamp()),
        'date': now.strftime('%Y-%m-%d'),
        'time': now.strftime('%H:%M:%S'),
        'time_12h': time_12h,
        'day_of_week': now.strftime('%A'),
        'human_date': human_date,
        'human': f'{human_date} at {time_12h}',
        'iso_week': f'{iso_year}-W{iso_week:02d}',
        'timezone': os.getenv('TZ') or now.tzname() or '',
        'utc_offset': utc_offset,
    }


@mcp.tool()
def get_current_timestamp() -> Dict[str, Any]:
    '''
    Get the current local date and time (TZ timezone) in every common format.

    Returns:
        Dictionary with:
            iso: ISO 8601 local timestamp with offset (2026-11-08T14:32:05-05:00)
            utc: ISO 8601 UTC timestamp (2026-11-08T19:32:05Z)
            unix: seconds since the epoch
            date: YYYY-MM-DD, the format journal tools take
            time: 24-hour HH:MM:SS
            time_12h: 12-hour time (2:32 PM)
            day_of_week: weekday name
            human_date: Sunday November 8, 2026
            human: Sunday November 8, 2026 at 2:32 PM
            iso_week: ISO week (2026-W45)
            timezone: timezone name
            utc_offset: offset from UTC (-05:00)
    '''
    try:
        logger.debug('get_current_timestamp called')
        with get_client() as vault:
            now = vault.get_local_datetime()
        result = format_timestamp(now)
        logger.info(f"current timestamp: {result['iso']} ({result['timezone']})")
        return result
    except Exception as e:
        logger.exception(f'unexpected error getting current timestamp: {e}')
        return create_error_response(f'Unexpected error getting current timestamp: {e}')


# journal tools

@mcp.tool()
def list_todays_journal_entry() -> Dict[str, Any]:
    '''
    Get today's journal entry path in the format journal/YYYY/MM/YYYY-MM-DD.md.

    A day's file holds one or more entries. Each entry starts with a ### heading and
    uses #### and ##### headings to organize within it. Never add a date heading,
    Obsidian handles this.

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


@mcp.tool()
def read_journal_entry(date: str) -> Dict[str, Any]:
    '''
    Read the journal entry for a specific date.

    Args:
        date: Date in YYYY-MM-DD format (e.g., "2025-10-27")

    Returns:
        Dictionary with the entry path, whether it exists, and its content
    '''
    try:
        logger.debug(f'read_journal_entry called: date={date}')
        validated_input = JournalDateInput(date=date)
        entry_date = datetime.strptime(validated_input.date, '%Y-%m-%d')

        with get_client() as vault:
            return vault.read_journal_entry(entry_date)

    except ValidationError as e:
        logger.error(f'validation error reading journal entry: {e}')
        return create_error_response(f'Invalid input: {e}')
    except VaultError as e:
        logger.error(f'vault error reading journal entry: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error reading journal entry: {e}')
        return create_error_response(f'Unexpected error reading journal entry: {e}')


@mcp.tool()
def write_journal_entry(content: str, date: Optional[str] = None) -> Dict[str, Any]:
    '''
    Replace the whole content of a journal entry file, creating it if needed.

    Read the entry first with read_journal_entry and preserve existing entries. Use this
    to edit or reorganize existing entries; to add a new entry, prefer
    append_to_journal_entry or prepend_to_journal_entry, which never touch existing content.
    Entries start with a ### heading and use #### and ##### headings within.

    Args:
        content: Full markdown content of the file
        date: Date in YYYY-MM-DD format (defaults to today)

    Returns:
        Dictionary with success indicator, the entry path, and whether it was created
    '''
    try:
        logger.debug(f'write_journal_entry called: date={date} ({len(content)} chars)')
        validated_input = JournalWriteInput(content=content, date=date)

        with get_client() as vault:
            result = vault.write_journal_entry(validated_input.content, validated_input.entry_date())
            return {**create_success_response(), **result}

    except ValidationError as e:
        logger.error(f'validation error writing journal entry: {e}')
        return create_error_response(f'Invalid input: {e}')
    except VaultError as e:
        logger.error(f'vault error writing journal entry: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error writing journal entry: {e}')
        return create_error_response(f'Unexpected error writing journal entry: {e}')


@mcp.tool()
def append_to_journal_entry(text: str, date: Optional[str] = None) -> Dict[str, Any]:
    '''
    Append text to the end of a journal entry file, separated by a blank line.

    Creates the file if it does not exist yet. Existing content is never changed.
    Start the text with a ### heading to add a new entry (#### and ##### within it);
    text without a heading continues the last entry.

    Args:
        text: Text to append (markdown allowed)
        date: Date in YYYY-MM-DD format (defaults to today)

    Returns:
        Dictionary with success indicator, the entry path, and whether it was created
    '''
    try:
        logger.debug(f'append_to_journal_entry called: date={date} ({len(text)} chars)')
        validated_input = JournalTextInput(text=text, date=date)

        with get_client() as vault:
            result = vault.append_to_journal(validated_input.text, validated_input.entry_date())
            return {**create_success_response(), **result}

    except ValidationError as e:
        logger.error(f'validation error appending to journal: {e}')
        return create_error_response(f'Invalid input: {e}')
    except VaultError as e:
        logger.error(f'vault error appending to journal: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error appending to journal: {e}')
        return create_error_response(f'Unexpected error appending to journal: {e}')


@mcp.tool()
def prepend_to_journal_entry(text: str, date: Optional[str] = None) -> Dict[str, Any]:
    '''
    Insert text at the top of a journal entry file, separated by a blank line.

    Creates the file if it does not exist yet. YAML frontmatter stays first; all other
    existing content is kept unchanged below the new text. The text should be a complete
    entry starting with a ### heading (#### and ##### within it).

    Args:
        text: Text to prepend (markdown allowed)
        date: Date in YYYY-MM-DD format (defaults to today)

    Returns:
        Dictionary with success indicator, the entry path, and whether it was created
    '''
    try:
        logger.debug(f'prepend_to_journal_entry called: date={date} ({len(text)} chars)')
        validated_input = JournalTextInput(text=text, date=date)

        with get_client() as vault:
            result = vault.prepend_to_journal(validated_input.text, validated_input.entry_date())
            return {**create_success_response(), **result}

    except ValidationError as e:
        logger.error(f'validation error prepending to journal: {e}')
        return create_error_response(f'Invalid input: {e}')
    except VaultError as e:
        logger.error(f'vault error prepending to journal: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error prepending to journal: {e}')
        return create_error_response(f'Unexpected error prepending to journal: {e}')


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
