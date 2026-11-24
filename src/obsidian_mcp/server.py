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
from typing import Annotated, Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field, ValidationError

from obsidian_mcp.schema import (
    FilePathInput,
    FileWriteInput,
    JournalDateInput,
    JournalNoteInput,
    JournalSearchInput,
    JournalTextInput,
    JournalWriteInput,
    ProjectInput,
    YearMonthInput,
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


def tool_error(message: str) -> ToolError:
    '''
    A tool error to raise, so the client sees the call failed, with the vault's location removed.
    '''
    return ToolError(redact_vault_path(message))


def invalid_input(error: ValidationError) -> str:
    '''A short message for a validation error: each problem and its argument, without pydantic's links.'''
    problems = []
    for item in error.errors():
        field = '.'.join(str(part) for part in item['loc'])
        message = item['msg'].removeprefix('Value error, ')
        problems.append(f'{field}: {message}' if field else message)
    return 'Invalid input: ' + '; '.join(problems)


# guidance sent to clients as the server instructions: the journal format, then projects and the wiki

JOURNAL_FORMAT = '''
journal files live at journal/YYYY/MM/YYYY-MM-DD.md, one file per day. never add a date
heading or title to the file, obsidian handles this.

notes are added to the end of a day's file through the day. anything that belongs above
them, such as a daily recap, is prepended.

dates:
- before reading or writing the journal, call get_todays_date; don't rely on your own
  sense of the date. "today" means the date in the user's timezone (TZ).
- if it's after midnight and the user hasn't slept, or is catching up on an earlier day,
  confirm the date with them and pass it explicitly as date (YYYY-MM-DD).

adding a note, the usual way to write to the journal:
- add_note_to_journal_entry appends a note to the end of the file, creating the file if
  needed, and stamps it with the time. never write a timestamp yourself.
- a note must start with a ### heading naming its topic. organize longer notes with ####
  sections and ##### subsections, without skipping levels.
- the note is written exactly as you send it, so lay it out yourself: a blank line after
  every heading, and a blank line before every heading after the first. the tool adds a
  blank line, the timestamp and two blank lines after the note. the full format is in the
  add_note_to_journal_entry description.
- write in first person, natural voice, valuable to read months later. keep quick
  references (links, commands, snippets, todos) in a #### section inside the note.

other edits (date is YYYY-MM-DD, defaults to today):
- prepend_to_journal_entry writes text exactly as given at the top of the file, after any
  yaml frontmatter. use it for sections above the notes, such as a # daily recap. nothing
  is added, so end the text with a blank line to separate it from what follows.
- append_to_journal_entry writes text exactly as given at the end of the file. nothing is
  added, so include the newlines you need.
- write_journal_entry replaces the whole file. read it first with read_journal_entry and
  keep everything you aren't changing; use it only to edit or reorganize existing content.

finding past notes:
- search_journal finds notes containing every word in the query, newest first, and
  returns snippets. use it when the user asks about something they wrote before but
  doesn't give the date, then read_journal_entry for the full day.

projects and the wiki:
- projects are folders of notes for ongoing work. list_project_content gives the paths
  that read_file and write_file take.
- the wiki is a set of standalone articles. list_wiki gives the paths that read_file takes.
- when the user asks for something to be documented, add it to the journal and to a
  project file, reading an existing file first.
'''

# tool annotations: whether a tool only reads, and whether a write can overwrite or remove
# existing content. every tool works on the vault alone, so none is open world.

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)
ADDS = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)
REPLACES = ToolAnnotations(readOnlyHint=False, destructiveHint=True, openWorldHint=False)

# argument descriptions shared by several tools

EntryDate = Annotated[str, Field(description='the day, as YYYY-MM-DD')]
OptionalEntryDate = Annotated[
    Optional[str], Field(description='the day, as YYYY-MM-DD; today if left out')
]

# mcp server; tools are listed to clients in the order they are defined, the usual ones first

mcp = FastMCP('Obsidian MCP', instructions=JOURNAL_FORMAT)


# journal tools

@mcp.tool(title="Add a journal note", annotations=ADDS)
def add_note_to_journal_entry(
    text: Annotated[str, Field(
        description='the note, starting with a ### heading, laid out as the description shows'
    )],
    date: Annotated[Optional[str], Field(
        description='the day, as YYYY-MM-DD; today if left out. pass the previous day when '
                    'the user is still on it after midnight'
    )] = None,
) -> Dict[str, Any]:
    '''
    Add a note to the end of a journal entry. This is the usual way to write to the journal.

    Creates the file if needed, then appends the note and stamps it with the current time
    below it. Never write a timestamp yourself. Existing content is never changed.

    The note is written exactly as you send it, spacing included, so send it in this
    format: a ### heading naming the topic (required), a blank line, the content; for each section,
    a blank line, a #### heading, a blank line, its content (##### for subsections, the
    same way). For example:

        ### River trail run

        first time on the new trail, much better than the road loop

        #### Notes

        - 5.2 miles, mostly flat

    The tool trims the ends of the note and then adds a blank line, the timestamp
    (YYYY-MM-DD HH:MM) and two blank lines, so don't end the note with blank lines.

    Returns a dictionary with success indicator, the entry path, whether it was created,
    and the timestamp added.
    '''
    try:
        logger.debug(f'add_note_to_journal_entry called: date={date} ({len(text)} chars)')
        validated_input = JournalNoteInput(text=text, date=date)

        with get_client() as vault:
            result = vault.add_note_to_journal(validated_input.text, validated_input.entry_date())
            return {**create_success_response(), **result}

    except ValidationError as e:
        logger.error(f'validation error adding note to journal: {e}')
        raise tool_error(invalid_input(e))
    except VaultError as e:
        logger.error(f'vault error adding note to journal: {e}')
        raise tool_error(str(e))
    except Exception as e:
        logger.exception(f'unexpected error adding note to journal: {e}')
        raise tool_error(f'Unexpected error adding note to journal: {e}')


@mcp.tool(title="Read a journal entry", annotations=READ_ONLY)
def read_journal_entry(date: EntryDate) -> Dict[str, Any]:
    '''
    Read the journal entry for a specific date.

    Returns a dictionary with the entry path, whether it exists, and its content.
    '''
    try:
        logger.debug(f'read_journal_entry called: date={date}')
        validated_input = JournalDateInput(date=date)
        entry_date = datetime.strptime(validated_input.date, '%Y-%m-%d')

        with get_client() as vault:
            return vault.read_journal_entry(entry_date)

    except ValidationError as e:
        logger.error(f'validation error reading journal entry: {e}')
        raise tool_error(invalid_input(e))
    except VaultError as e:
        logger.error(f'vault error reading journal entry: {e}')
        raise tool_error(str(e))
    except Exception as e:
        logger.exception(f'unexpected error reading journal entry: {e}')
        raise tool_error(f'Unexpected error reading journal entry: {e}')


@mcp.tool(title="Search the journal", annotations=READ_ONLY)
def search_journal(
    query: Annotated[str, Field(
        description="words to find, e.g. 'dentist insurance' or '\"river trail\" run'"
    )],
    start_date: Annotated[Optional[str], Field(
        description='the earliest entry date to search, as YYYY-MM-DD; no limit if left out'
    )] = None,
    end_date: Annotated[Optional[str], Field(
        description='the latest entry date to search, as YYYY-MM-DD; no limit if left out'
    )] = None,
    max_results: Annotated[int, Field(
        description='the most notes to return, from 1 to 50'
    )] = 20,
) -> Dict[str, Any]:
    '''
    Search journal notes by keyword, newest first.

    Each ### note in an entry is searched on its own (text above the first note, such as
    a recap, counts as one more). A note matches when it contains every word in the query,
    ignoring case; put words in double quotes to match them as an exact phrase. This is
    keyword search, not semantic: use two or three distinctive words, and if nothing comes
    back try synonyms, fewer words, or a single word. Narrow with start_date and end_date
    when you know roughly when something happened.

    Results are short snippets. Read the full entry with read_journal_entry and the result's
    date. When truncated is true, more notes matched than were returned; narrow the dates
    or the query rather than raising max_results.

    Returns a dictionary with results (each with date, path, heading, timestamp, snippet),
    total_matches, truncated, and entries_searched.
    '''
    try:
        logger.debug(f'search_journal called: query={query!r}, start={start_date}, end={end_date}')
        validated_input = JournalSearchInput(
            query=query, start_date=start_date, end_date=end_date, max_results=max_results
        )

        with get_client() as vault:
            result = vault.search_journal(
                validated_input.terms(),
                validated_input.start_date,
                validated_input.end_date,
                validated_input.max_results,
            )
            return {'query': validated_input.query, **result}

    except ValidationError as e:
        logger.error(f'validation error searching journal: {e}')
        raise tool_error(invalid_input(e))
    except VaultError as e:
        logger.error(f'vault error searching journal: {e}')
        raise tool_error(str(e))
    except Exception as e:
        logger.exception(f'unexpected error searching journal: {e}')
        raise tool_error(f'Unexpected error searching journal: {e}')


@mcp.tool(title="Get today's date", annotations=READ_ONLY)
def get_todays_date() -> Dict[str, Any]:
    '''
    Get today's date and the current time in the user's timezone (TZ).

    This is the source of truth for "today". Call it before reading or writing a journal
    entry instead of relying on your own sense of the date; pass its date field to the
    journal tools. Check the time too: after midnight the user may still mean the
    previous day.

    Returns a dictionary with:

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
        raise tool_error(f"Unexpected error getting today's date: {e}")


@mcp.tool(title="List journal entries for a month", annotations=READ_ONLY)
def list_journal_entries_by_year_and_month(
    year: Annotated[str, Field(description='the year, as YYYY, e.g. "2025"')],
    month: Annotated[str, Field(
        description='the month, as MM with a leading zero, e.g. "01" for January'
    )],
) -> List[Dict[str, str]]:
    '''
    List all journal entries for a specific year and month.
    Journal entries are organized as journal/YYYY/MM/YYYY-MM-DD.md.

    Returns a list of journal entries with metadata.
    '''
    try:
        logger.debug(f'list_journal_entries_by_year_and_month called: year={year}, month={month}')
        validated_input = YearMonthInput(year=year, month=month)

        with get_client() as vault:
            entries = vault.list_journal_entries(validated_input.year, validated_input.month)
            return entries

    except ValidationError as e:
        logger.error(f'validation error listing journal entries: {e}')
        raise tool_error(invalid_input(e))
    except VaultError as e:
        logger.error(f'vault error listing journal entries: {e}')
        raise tool_error(str(e))
    except Exception as e:
        logger.exception(f'unexpected error listing journal entries: {e}')
        raise tool_error(f'Unexpected error listing journal entries: {e}')


@mcp.tool(title="Prepend to a journal entry", annotations=ADDS)
def prepend_to_journal_entry(
    text: Annotated[str, Field(
        description='the text, written exactly as given; end it with a blank line'
    )],
    date: OptionalEntryDate = None,
) -> Dict[str, Any]:
    '''
    Insert text at the top of a journal entry file, exactly as given.

    Creates the file if it does not exist yet. YAML frontmatter stays first and the text
    goes right after it; all other existing content is kept unchanged below. Nothing is
    added between the text and what follows, so end the text with the newlines you need
    (usually a blank line). Use it for sections above the notes, such as a recap.

    Returns a dictionary with success indicator, the entry path, and whether it was
    created.
    '''
    try:
        logger.debug(f'prepend_to_journal_entry called: date={date} ({len(text)} chars)')
        validated_input = JournalTextInput(text=text, date=date)

        with get_client() as vault:
            result = vault.prepend_to_journal(validated_input.text, validated_input.entry_date())
            return {**create_success_response(), **result}

    except ValidationError as e:
        logger.error(f'validation error prepending to journal: {e}')
        raise tool_error(invalid_input(e))
    except VaultError as e:
        logger.error(f'vault error prepending to journal: {e}')
        raise tool_error(str(e))
    except Exception as e:
        logger.exception(f'unexpected error prepending to journal: {e}')
        raise tool_error(f'Unexpected error prepending to journal: {e}')


@mcp.tool(title="Append to a journal entry", annotations=ADDS)
def append_to_journal_entry(
    text: Annotated[str, Field(
        description='the text, written exactly as given; include the newlines you need'
    )],
    date: OptionalEntryDate = None,
) -> Dict[str, Any]:
    '''
    Append text to the end of a journal entry file, exactly as given.

    Creates the file if it does not exist yet. Existing content is never changed.
    Nothing is added: no blank line before the text and no newline after it, so include
    the newlines you need. To add a note, use add_note_to_journal_entry instead.

    Returns a dictionary with success indicator, the entry path, and whether it was
    created.
    '''
    try:
        logger.debug(f'append_to_journal_entry called: date={date} ({len(text)} chars)')
        validated_input = JournalTextInput(text=text, date=date)

        with get_client() as vault:
            result = vault.append_to_journal(validated_input.text, validated_input.entry_date())
            return {**create_success_response(), **result}

    except ValidationError as e:
        logger.error(f'validation error appending to journal: {e}')
        raise tool_error(invalid_input(e))
    except VaultError as e:
        logger.error(f'vault error appending to journal: {e}')
        raise tool_error(str(e))
    except Exception as e:
        logger.exception(f'unexpected error appending to journal: {e}')
        raise tool_error(f'Unexpected error appending to journal: {e}')


@mcp.tool(title="Replace a journal entry", annotations=REPLACES)
def write_journal_entry(
    content: Annotated[str, Field(
        description="the whole file, everything you aren't changing included"
    )],
    date: OptionalEntryDate = None,
) -> Dict[str, Any]:
    '''
    Replace the whole content of a journal entry file, creating it if needed.

    Read the entry first with read_journal_entry and keep everything you aren't changing.
    Use this only to edit or reorganize existing content; to add a note, use
    add_note_to_journal_entry, which never touches existing content.

    Returns a dictionary with success indicator, the entry path, and whether it was
    created.
    '''
    try:
        logger.debug(f'write_journal_entry called: date={date} ({len(content)} chars)')
        validated_input = JournalWriteInput(content=content, date=date)

        with get_client() as vault:
            result = vault.write_journal_entry(validated_input.content, validated_input.entry_date())
            return {**create_success_response(), **result}

    except ValidationError as e:
        logger.error(f'validation error writing journal entry: {e}')
        raise tool_error(invalid_input(e))
    except VaultError as e:
        logger.error(f'vault error writing journal entry: {e}')
        raise tool_error(str(e))
    except Exception as e:
        logger.exception(f'unexpected error writing journal entry: {e}')
        raise tool_error(f'Unexpected error writing journal entry: {e}')


# project tools

@mcp.tool(title="List projects", annotations=READ_ONLY)
def list_projects() -> List[Dict[str, str]]:
    '''
    List all projects (subdirectories in the projects directory).

    Projects are simple directory-based organization for ongoing work. Use spaces in
    project names (e.g., "home automation", "blog redesign") and organize related
    documentation within each project directory.

    Returns a list of project directories with metadata.
    '''
    try:
        logger.debug('list_projects called')
        with get_client() as vault:
            return vault.list_projects()
    except VaultError as e:
        logger.error(f'vault error listing projects: {e}')
        raise tool_error(str(e))
    except Exception as e:
        logger.exception(f'unexpected error listing projects: {e}')
        raise tool_error(f'Unexpected error listing projects: {e}')


@mcp.tool(title="List a project's files", annotations=READ_ONLY)
def list_project_content(
    project: Annotated[str, Field(description='the project name, from list_projects')],
) -> List[Dict[str, str]]:
    '''
    List all files and directories within a project.

    Returns a list of files and directories with metadata.
    '''
    try:
        logger.debug(f'list_project_content called: project={project}')
        validated_input = ProjectInput(project=project)

        with get_client() as vault:
            return vault.list_project_content(validated_input.project)

    except ValidationError as e:
        logger.error(f'validation error listing project content: {e}')
        raise tool_error(invalid_input(e))
    except VaultError as e:
        logger.error(f'vault error listing project content: {e}')
        raise tool_error(str(e))
    except Exception as e:
        logger.exception(f'unexpected error listing project content: {e}')
        raise tool_error(f'Unexpected error listing project content: {e}')


@mcp.tool(title="Create a project", annotations=ADDS)
def create_project(
    project: Annotated[str, Field(
        description='the new project name, lowercase words with spaces'
    )],
) -> Dict[str, Any]:
    '''
    Create a new project directory.

    Returns a success indicator or error message.
    '''
    try:
        logger.debug(f'create_project called: project={project}')
        validated_input = ProjectInput(project=project)

        with get_client() as vault:
            vault.create_project(validated_input.project)
            return create_success_response()

    except ValidationError as e:
        logger.error(f'validation error creating project: {e}')
        raise tool_error(invalid_input(e))
    except VaultError as e:
        logger.error(f'vault error creating project: {e}')
        raise tool_error(str(e))
    except Exception as e:
        logger.exception(f'unexpected error creating project: {e}')
        raise tool_error(f'Unexpected error creating project: {e}')


# wiki tools

@mcp.tool(title="List wiki articles", annotations=READ_ONLY)
def list_wiki() -> List[Dict[str, str]]:
    '''
    List all wiki articles in the obsidian wiki.

    Wiki articles are comprehensive, standalone documentation on specific topics. Use
    descriptive filenames with spaces in lowercase (e.g., "python asyncio.md", "docker
    networking.md") in a flat directory structure for easy discovery.

    Returns a list of markdown files with metadata.
    '''
    try:
        logger.debug('list_wiki called')
        with get_client() as vault:
            return vault.list_wiki()
    except VaultError as e:
        logger.error(f'vault error listing wiki: {e}')
        raise tool_error(str(e))
    except Exception as e:
        logger.exception(f'unexpected error listing wiki: {e}')
        raise tool_error(f'Unexpected error listing wiki: {e}')


# file tools

@mcp.tool(title="Read a vault file", annotations=READ_ONLY)
def read_file(
    file_path: Annotated[str, Field(
        description='the vault-relative path, from list_project_content or list_wiki'
    )],
) -> Dict[str, Any]:
    '''
    Read file content from the Obsidian vault.

    Returns a dictionary with file content or error message.
    '''
    try:
        logger.debug(f'read_file called with path: {file_path}')
        validated_input = FilePathInput(file_path=file_path)

        with get_client() as vault:
            content = vault.read_file(validated_input.file_path)
            return {'content': content}

    except ValidationError as e:
        logger.error(f'validation error reading file: {e}')
        raise tool_error(invalid_input(e))
    except VaultError as e:
        logger.error(f'vault error reading file: {e}')
        raise tool_error(str(e))
    except Exception as e:
        logger.exception(f'unexpected error reading file: {e}')
        raise tool_error(f'Unexpected error reading file: {e}')


@mcp.tool(title="Write a vault file", annotations=REPLACES)
def write_file(
    file_path: Annotated[str, Field(
        description='the vault-relative path; read the file first if it exists'
    )],
    content: Annotated[str, Field(description='the whole file, replacing what is there')],
) -> Dict[str, Any]:
    '''
    Write content to a file in the Obsidian vault.
    It's good practice to read from a file before writing to ensure nothing is overwritten.
    For journal files, use write_journal_entry, append_to_journal_entry, or
    prepend_to_journal_entry instead.

    Returns a dictionary with success indicator or error message.
    '''
    try:
        logger.debug(f'write_file called with path: {file_path} ({len(content)} chars)')
        validated_input = FileWriteInput(file_path=file_path, content=content)

        with get_client() as vault:
            vault.write_file(validated_input.file_path, validated_input.content)
            return create_success_response()

    except ValidationError as e:
        logger.error(f'validation error writing file: {e}')
        raise tool_error(invalid_input(e))
    except VaultError as e:
        logger.error(f'vault error writing file: {e}')
        raise tool_error(str(e))
    except Exception as e:
        logger.exception(f'unexpected error writing file: {e}')
        raise tool_error(f'Unexpected error writing file: {e}')


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
