'''
Obsidian MCP server with FastMCP tools.

Provides MCP tools for interacting with an Obsidian vault including
file operations, journal management, project organization, and wiki articles.
'''

import argparse
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from obsidian_mcp.schema import (
    FilePathInput,
    FileWriteInput,
    JournalDateInput,
    JournalNoteInput,
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


def redact_vault_path(message: str) -> str:
    '''
    Replace the vault's absolute location in a message with <vault>.

    Tools only ever speak in vault-relative paths; this is the backstop for any error
    text (an exception message, a repr with doubled backslashes) that still holds it.
    '''
    if _client is None:
        return message
    root = str(_client.vault_path)
    forms = {root, root.replace('\\', '\\\\'), root.replace('\\', '/')}
    for form in sorted(forms, key=len, reverse=True):
        message = re.sub(re.escape(form), '<vault>', message, flags=re.IGNORECASE)
    return message


def error_response(message: str) -> Dict[str, Any]:
    '''An error response, with the vault's location removed.'''
    return create_error_response(redact_vault_path(message))


def format_error(error: Exception) -> Dict[str, Any]:
    '''Format an exception as an error response.'''
    return error_response(str(error))


# journal format guidance, sent to clients as the server instructions

JOURNAL_FORMAT = '''
journal files live at journal/YYYY/MM/YYYY-MM-DD.md, one file per day. never add a date
heading or title to the file, obsidian handles this.

a day's file has a # Daily Notes section that notes are added to through the day. other
top-level (#) sections, such as a daily recap, go above it.

dates:
- before reading or writing the journal, call get_todays_date; don't rely on your own
  sense of the date. "today" means the date in the user's timezone (TZ).
- if it's after midnight and the user hasn't slept, or is catching up on an earlier day,
  confirm the date with them and pass it explicitly as date (YYYY-MM-DD).

adding a note, the usual way to write to the journal:
- add_note_to_journal_entry appends a note to the # Daily Notes section, creating the file
  and the section if needed, and stamps it with the time. never write a timestamp yourself.
- a note starts with a ### heading naming its topic, then the note on the next line.
  organize longer notes with #### sections and ##### subsections, without skipping levels.
  never use # or ## headings in a note.
- write in first person, natural voice, valuable to read months later. keep quick
  references (links, commands, snippets, todos) in a #### section inside the note.

other edits (date is YYYY-MM-DD, defaults to today):
- prepend_to_journal_entry writes text exactly as given at the top of the file, after any
  yaml frontmatter. use it for sections above the notes, such as a # Daily Recap. nothing
  is added, so end the text with a blank line to separate it from what follows.
- append_to_journal_entry writes text exactly as given at the end of the file. nothing is
  added, so include the newlines you need.
- write_journal_entry replaces the whole file. read it first with read_journal_entry and
  keep everything you aren't changing; use it only to edit or reorganize existing content.
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
        return error_response(f'Invalid input: {e}')
    except VaultError as e:
        logger.error(f'vault error reading file: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error reading file: {e}')
        return error_response(f'Unexpected error reading file: {e}')


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
        return error_response(f'Invalid input: {e}')
    except VaultError as e:
        logger.error(f'vault error writing file: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error writing file: {e}')
        return error_response(f'Unexpected error writing file: {e}')


# date tools

@mcp.tool()
def get_todays_date() -> Dict[str, Any]:
    '''
    Get today's date and the current time in the user's timezone (TZ).

    This is the source of truth for "today". Call it before reading or writing a journal
    entry instead of relying on your own sense of the date; pass its date field to the
    journal tools. Check the time too: after midnight the user may still mean the
    previous day.

    Returns:
        Dictionary with:
            date: YYYY-MM-DD, the format journal tools take (2026-11-14)
            time: 12-hour time with AM or PM (2:32 PM)
            day_of_week: weekday name (Saturday)
            timezone: timezone name (America/New_York)
    '''
    try:
        logger.debug('get_todays_date called')
        with get_client() as vault:
            now = vault.get_local_datetime()
        result = {
            'date': now.strftime('%Y-%m-%d'),
            # built by hand: %p follows the system locale, which may not say AM/PM
            'time': f"{now.hour % 12 or 12}:{now.minute:02d} {'AM' if now.hour < 12 else 'PM'}",
            'day_of_week': now.strftime('%A'),
            'timezone': os.getenv('TZ') or now.tzname() or '',
        }
        logger.info(f"today's date: {result['date']} {result['time']} ({result['timezone']})")
        return result
    except Exception as e:
        logger.exception(f"unexpected error getting today's date: {e}")
        return error_response(f"Unexpected error getting today's date: {e}")


# journal tools

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
        return [error_response(f'Invalid input: {e}')]
    except VaultError as e:
        logger.error(f'vault error listing journal entries: {e}')
        return [format_error(e)]
    except Exception as e:
        logger.exception(f'unexpected error listing journal entries: {e}')
        return [error_response(f'Unexpected error listing journal entries: {e}')]


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
        return error_response(f'Invalid input: {e}')
    except VaultError as e:
        logger.error(f'vault error reading journal entry: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error reading journal entry: {e}')
        return error_response(f'Unexpected error reading journal entry: {e}')


@mcp.tool()
def write_journal_entry(content: str, date: Optional[str] = None) -> Dict[str, Any]:
    '''
    Replace the whole content of a journal entry file, creating it if needed.

    Read the entry first with read_journal_entry and keep everything you aren't changing.
    Use this only to edit or reorganize existing content; to add a note, use
    add_note_to_journal_entry, which never touches existing content.

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
        return error_response(f'Invalid input: {e}')
    except VaultError as e:
        logger.error(f'vault error writing journal entry: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error writing journal entry: {e}')
        return error_response(f'Unexpected error writing journal entry: {e}')


@mcp.tool()
def append_to_journal_entry(text: str, date: Optional[str] = None) -> Dict[str, Any]:
    '''
    Append text to the end of a journal entry file, exactly as given.

    Creates the file if it does not exist yet. Existing content is never changed.
    Nothing is added: no blank line before the text and no newline after it, so include
    the newlines you need. To add a note, use add_note_to_journal_entry instead.

    Args:
        text: Text to append, written byte for byte (markdown allowed)
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
        return error_response(f'Invalid input: {e}')
    except VaultError as e:
        logger.error(f'vault error appending to journal: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error appending to journal: {e}')
        return error_response(f'Unexpected error appending to journal: {e}')


@mcp.tool()
def prepend_to_journal_entry(text: str, date: Optional[str] = None) -> Dict[str, Any]:
    '''
    Insert text at the top of a journal entry file, exactly as given.

    Creates the file if it does not exist yet. YAML frontmatter stays first and the text
    goes right after it; all other existing content is kept unchanged below. Nothing is
    added between the text and what follows, so end the text with the newlines you need
    (usually a blank line). Use it for sections above # Daily Notes, such as a recap.

    Args:
        text: Text to prepend, written byte for byte (markdown allowed)
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
        return error_response(f'Invalid input: {e}')
    except VaultError as e:
        logger.error(f'vault error prepending to journal: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error prepending to journal: {e}')
        return error_response(f'Unexpected error prepending to journal: {e}')


@mcp.tool()
def add_note_to_journal_entry(text: str, date: Optional[str] = None) -> Dict[str, Any]:
    '''
    Add a note to the # Daily Notes section of a journal entry. This is the usual way to
    write to the journal.

    Creates the file with a # Daily Notes section if needed, then appends the note and
    stamps it with the current time on the line after it. Never write a timestamp into
    the note yourself. Existing content is never changed.

    The note starts with a ### heading naming the topic, then the note on the next line.
    Organize longer notes with #### sections and ##### subsections; never use # or ##.

    Args:
        text: The note, starting with a ### heading (markdown allowed)
        date: Date in YYYY-MM-DD format (defaults to today). Pass the previous day when the
            user is still on it after midnight.

    Returns:
        Dictionary with success indicator, the entry path, whether it was created, and the
        timestamp added
    '''
    try:
        logger.debug(f'add_note_to_journal_entry called: date={date} ({len(text)} chars)')
        validated_input = JournalNoteInput(text=text, date=date)

        with get_client() as vault:
            result = vault.add_note_to_journal(validated_input.text, validated_input.entry_date())
            return {**create_success_response(), **result}

    except ValidationError as e:
        logger.error(f'validation error adding note to journal: {e}')
        return error_response(f'Invalid input: {e}')
    except VaultError as e:
        logger.error(f'vault error adding note to journal: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error adding note to journal: {e}')
        return error_response(f'Unexpected error adding note to journal: {e}')


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
        return [error_response(f'Unexpected error listing projects: {e}')]


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
        return [error_response(f'Invalid input: {e}')]
    except VaultError as e:
        logger.error(f'vault error listing project content: {e}')
        return [format_error(e)]
    except Exception as e:
        logger.exception(f'unexpected error listing project content: {e}')
        return [error_response(f'Unexpected error listing project content: {e}')]


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
        return error_response(f'Invalid input: {e}')
    except VaultError as e:
        logger.error(f'vault error creating project: {e}')
        return format_error(e)
    except Exception as e:
        logger.exception(f'unexpected error creating project: {e}')
        return error_response(f'Unexpected error creating project: {e}')


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
        return [error_response(f'Unexpected error listing wiki: {e}')]


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
