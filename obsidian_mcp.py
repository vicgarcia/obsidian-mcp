import argparse
import logging
import os
import re
import zoneinfo
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ValidationError, field_validator

logger = logging.getLogger(__name__)

_HELP = '''
environment variables:
  OBSIDIAN_VAULT_PATH   Path to the Obsidian vault directory
  TZ                    Timezone for journal dates (e.g., America/New_York)
  LOG_LEVEL             Logging level (debug or info, default: info)
'''

# module-level vault path set during run()
_vault_path: Optional[str] = None


# arg parsing

def parse_args() -> argparse.Namespace:
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


# pydantic validation models

class YearMonthInput(BaseModel):
    ''' Input validation for year/month operations. '''
    year: str
    month: str

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: str) -> str:
        if not re.match(r'^\d{4}$', v):
            raise ValueError("Year must be in YYYY format")
        year_int = int(v)
        if year_int < 1970 or year_int > 2100:
            raise ValueError("Year must be between 1970 and 2100")
        return v

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: str) -> str:
        if not re.match(r'^\d{2}$', v):
            raise ValueError("Month must be in MM format (01-12)")
        month_int = int(v)
        if month_int < 1 or month_int > 12:
            raise ValueError("Month must be between 01 and 12")
        return v


class FilePathInput(BaseModel):
    ''' Input validation for file path operations. '''
    file_path: str

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("File path cannot be empty")
        if ".." in v or v.startswith("/"):
            raise ValueError("Invalid file path: directory traversal not allowed")
        return v.strip()


class FileWriteInput(BaseModel):
    ''' Input validation for file write operations. '''
    file_path: str
    content: str

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("File path cannot be empty")
        if ".." in v or v.startswith("/"):
            raise ValueError("Invalid file path: directory traversal not allowed")
        return v.strip()


class ProjectInput(BaseModel):
    ''' Input validation for project operations. '''
    project: str

    @field_validator("project")
    @classmethod
    def validate_project(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("Project name cannot be empty")
        v = v.strip()
        invalid_chars = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]
        for char in invalid_chars:
            if char in v:
                raise ValueError(f"Project name cannot contain '{char}'")
        if ".." in v:
            raise ValueError("Project name cannot contain '..'")
        return v


# utility functions

def set_vault_path(path: str) -> None:
    ''' Set the module-level vault path. Called from run(). '''
    global _vault_path
    _vault_path = path
    logger.debug(f"vault path set to: {path}")


def get_vault_base() -> Path:
    ''' Get the vault base path from module-level variable or environment. '''
    vault_path = _vault_path or os.getenv('OBSIDIAN_VAULT_PATH')
    if not vault_path:
        logger.error("vault path is not configured")
        raise ValueError("vault path is required (--vault or OBSIDIAN_VAULT_PATH env var)")
    resolved_path = Path(vault_path).resolve()
    logger.debug(f"vault base path: {resolved_path}")
    return resolved_path


def validate_vault_path(file_path: str) -> Path:
    ''' Validate and resolve a vault-relative path. '''
    vault_base = get_vault_base()
    vault_path = vault_base / Path(file_path)
    if not vault_path.is_relative_to(vault_base):
        logger.warning(f"path traversal attempt blocked: {file_path}")
        raise ValueError(f"Invalid path: {file_path} is outside vault directory")
    logger.debug(f"validated vault path: {vault_path}")
    return vault_path


def create_error_response(message: str) -> Dict[str, Any]:
    ''' Create a standardized error response. '''
    return {"error": message, "success": False}


def create_success_response() -> Dict[str, bool]:
    ''' Create a standardized success response. '''
    return {"success": True}


def create_file_info(path: Path, relative_to: Path) -> Dict[str, str]:
    ''' Create file information object with vault-relative path. '''
    relative_path = path.relative_to(relative_to)
    return {
        "path": str(relative_path).replace("\\", "/"),
        "name": path.name
    }


def get_local_datetime() -> datetime:
    ''' Get current datetime in local timezone, falling back to system timezone. '''
    try:
        tz_name = os.getenv('TZ')
        if tz_name:
            tz = zoneinfo.ZoneInfo(tz_name)
            logger.debug(f"using timezone from TZ env var: {tz_name}")
            return datetime.now(tz)
        logger.debug("using system local timezone")
        return datetime.now().astimezone()
    except Exception as e:
        logger.warning(f"timezone detection failed, using naive datetime: {e}")
        return datetime.now()


def get_today_journal_path() -> str:
    ''' Get today's journal entry path in format: journal/YYYY/MM/YYYY-MM-DD.md '''
    today = get_local_datetime()
    return f"journal/{today.year}/{today.month:02d}/{today.year}-{today.month:02d}-{today.day:02d}.md"


def list_files_in_directory(directory: Path, vault_base: Path, recursive: bool = False) -> List[Dict[str, str]]:
    ''' List files in a directory with vault-relative paths. '''
    files = []
    if not directory.exists():
        logger.debug(f"directory does not exist: {directory}")
        return files
    try:
        if recursive:
            for item in directory.rglob("*"):
                if item.is_file():
                    files.append(create_file_info(item, vault_base))
        else:
            for item in directory.iterdir():
                if item.is_file():
                    files.append(create_file_info(item, vault_base))
        logger.debug(f"listed {len(files)} files in {directory} (recursive={recursive})")
    except PermissionError:
        logger.warning(f"permission denied reading directory: {directory}")
        pass
    return sorted(files, key=lambda x: x["name"])


def list_directories_in_directory(directory: Path, vault_base: Path) -> List[Dict[str, str]]:
    ''' List subdirectories in a directory with vault-relative paths. '''
    directories = []
    if not directory.exists():
        logger.debug(f"directory does not exist: {directory}")
        return directories
    try:
        for item in directory.iterdir():
            if item.is_dir():
                directories.append(create_file_info(item, vault_base))
        logger.debug(f"listed {len(directories)} directories in {directory}")
    except PermissionError:
        logger.warning(f"permission denied reading directory: {directory}")
        pass
    return sorted(directories, key=lambda x: x["name"])


def is_valid_journal_filename(filename: str, year: str, month: str) -> bool:
    ''' Check if a filename matches the expected journal entry format. '''
    pattern = f"^{year}-{month}-\\d{{2}}\\.md$"
    return bool(re.match(pattern, filename))


# mcp server

mcp = FastMCP('Obsidian MCP')


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
        logger.debug(f"read_file called with path: {file_path}")
        validated_input = FilePathInput(file_path=file_path)
        vault_path = validate_vault_path(validated_input.file_path)

        if not vault_path.exists():
            logger.warning(f"file not found: {validated_input.file_path}")
            return create_error_response(f"File not found: {validated_input.file_path}")

        if not vault_path.is_file():
            logger.warning(f"path is not a file: {validated_input.file_path}")
            return create_error_response(f"Path is not a file: {validated_input.file_path}")

        try:
            content = vault_path.read_text(encoding='utf-8')
            logger.info(f"successfully read file: {validated_input.file_path} ({len(content)} chars)")
            return {"content": content}
        except UnicodeDecodeError:
            logger.warning(f"cannot read binary file: {validated_input.file_path}")
            return create_error_response(f"Cannot read binary file: {validated_input.file_path}")

    except ValidationError as e:
        logger.error(f"validation error reading file: {e}")
        return create_error_response(f"Invalid input: {e}")
    except ValueError as e:
        logger.error(f"value error reading file: {e}")
        return create_error_response(str(e))
    except Exception as e:
        logger.exception(f"unexpected error reading file: {e}")
        return create_error_response(f"Unexpected error reading file: {e}")


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
        logger.debug(f"write_file called with path: {file_path} ({len(content)} chars)")
        validated_input = FileWriteInput(file_path=file_path, content=content)
        vault_path = validate_vault_path(validated_input.file_path)

        vault_path.parent.mkdir(parents=True, exist_ok=True)
        vault_path.write_text(validated_input.content, encoding='utf-8')
        logger.info(f"successfully wrote file: {validated_input.file_path}")

        return create_success_response()

    except ValidationError as e:
        logger.error(f"validation error writing file: {e}")
        return create_error_response(f"Invalid input: {e}")
    except ValueError as e:
        logger.error(f"value error writing file: {e}")
        return create_error_response(str(e))
    except Exception as e:
        logger.exception(f"unexpected error writing file: {e}")
        return create_error_response(f"Unexpected error writing file: {e}")


@mcp.tool()
def get_current_date() -> Dict[str, str]:
    '''
    Get the current date in both human-readable and YYYY-MM-DD formats.

    Returns:
        Dictionary with date in YYYY-MM-DD format and human-readable format
    '''
    try:
        logger.debug("get_current_date called")
        now = datetime.now()
        formatted_date = now.strftime("%Y-%m-%d")
        human_date = now.strftime("%A %B %d, %Y")
        logger.info(f"current date: {formatted_date} ({human_date})")
        return {
            "formatted": formatted_date,
            "human": human_date
        }
    except Exception as e:
        logger.exception(f"unexpected error getting current date: {e}")
        return create_error_response(f"Unexpected error getting current date: {e}")


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
        logger.debug("list_todays_journal_entry called")
        journal_path = get_today_journal_path()
        logger.info(f"today's journal path: {journal_path}")
        return {
            "path": journal_path,
            "name": Path(journal_path).name
        }
    except ValueError as e:
        logger.error(f"value error getting today's journal entry: {e}")
        return create_error_response(str(e))
    except Exception as e:
        logger.exception(f"unexpected error getting today's journal entry: {e}")
        return create_error_response(f"Unexpected error getting today's journal entry: {e}")


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
    today = now.strftime("%A %B %d, %Y")
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
        logger.debug(f"list_journal_entries_by_year_and_month called: year={year}, month={month}")
        validated_input = YearMonthInput(year=year, month=month)

        vault_base = get_vault_base()
        journal_dir = vault_base / "journal" / validated_input.year / validated_input.month

        files = list_files_in_directory(journal_dir, vault_base)

        journal_entries = []
        for file_info in files:
            file_path = Path(file_info["path"])
            if file_path.suffix == ".md" and is_valid_journal_filename(file_path.name, validated_input.year, validated_input.month):
                journal_entries.append(file_info)

        logger.info(f"found {len(journal_entries)} journal entries for {year}/{month}")
        return sorted(journal_entries, key=lambda x: x["name"])

    except ValidationError as e:
        logger.error(f"validation error listing journal entries: {e}")
        return [create_error_response(f"Invalid input: {e}")]
    except ValueError as e:
        logger.error(f"value error listing journal entries: {e}")
        return [create_error_response(str(e))]
    except Exception as e:
        logger.exception(f"unexpected error listing journal entries: {e}")
        return [create_error_response(f"Unexpected error listing journal entries: {e}")]


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
        logger.debug("list_projects called")
        vault_base = get_vault_base()
        projects_dir = vault_base / "projects"

        projects = list_directories_in_directory(projects_dir, vault_base)
        logger.info(f"found {len(projects)} projects")

        return projects

    except ValueError as e:
        logger.error(f"value error listing projects: {e}")
        return [create_error_response(str(e))]
    except Exception as e:
        logger.exception(f"unexpected error listing projects: {e}")
        return [create_error_response(f"Unexpected error listing projects: {e}")]


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
        logger.debug(f"list_project_content called: project={project}")
        validated_input = ProjectInput(project=project)

        vault_base = get_vault_base()
        project_dir = vault_base / "projects" / validated_input.project

        if not project_dir.exists():
            logger.warning(f"project not found: {validated_input.project}")
            return [create_error_response(f"Project not found: {validated_input.project}")]

        if not project_dir.is_dir():
            logger.warning(f"project is not a directory: {validated_input.project}")
            return [create_error_response(f"Project is not a directory: {validated_input.project}")]

        files = list_files_in_directory(project_dir, vault_base, recursive=True)
        logger.info(f"found {len(files)} files in project: {validated_input.project}")

        return files

    except ValidationError as e:
        logger.error(f"validation error listing project content: {e}")
        return [create_error_response(f"Invalid input: {e}")]
    except ValueError as e:
        logger.error(f"value error listing project content: {e}")
        return [create_error_response(str(e))]
    except Exception as e:
        logger.exception(f"unexpected error listing project content: {e}")
        return [create_error_response(f"Unexpected error listing project content: {e}")]


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
        logger.debug(f"create_project called: project={project}")
        validated_input = ProjectInput(project=project)

        vault_base = get_vault_base()
        project_dir = vault_base / "projects" / validated_input.project

        project_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"successfully created project: {validated_input.project}")

        return create_success_response()

    except ValidationError as e:
        logger.error(f"validation error creating project: {e}")
        return create_error_response(f"Invalid input: {e}")
    except ValueError as e:
        logger.error(f"value error creating project: {e}")
        return create_error_response(str(e))
    except Exception as e:
        logger.exception(f"unexpected error creating project: {e}")
        return create_error_response(f"Unexpected error creating project: {e}")


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
        logger.debug("list_wiki called")
        vault_base = get_vault_base()
        wiki_dir = vault_base / "wiki"

        files = list_files_in_directory(wiki_dir, vault_base, recursive=False)
        articles = [f for f in files if Path(f["path"]).suffix == ".md"]

        logger.info(f"found {len(articles)} wiki articles")
        return articles

    except ValueError as e:
        logger.error(f"value error listing wiki: {e}")
        return [create_error_response(str(e))]
    except Exception as e:
        logger.exception(f"unexpected error listing wiki: {e}")
        return [create_error_response(f"Unexpected error listing wiki: {e}")]


# entry point

def run():
    logging.basicConfig(
        level=logging.DEBUG if os.getenv('LOG_LEVEL', 'info').lower() == 'debug' else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    args = parse_args()

    if not args.vault:
        logger.error('vault path is required (--vault or OBSIDIAN_VAULT_PATH env var)')
        raise SystemExit(1)

    set_vault_path(args.vault)

    logger.info('starting Obsidian MCP server')

    try:
        vault_base = get_vault_base()
        logger.info(f'vault path configured: {vault_base}')

        if not vault_base.exists():
            logger.error(f'vault directory does not exist: {vault_base}')
            raise SystemExit(1)

        if not vault_base.is_dir():
            logger.error(f'vault path is not a directory: {vault_base}')
            raise SystemExit(1)

        mcp.run()

    except KeyboardInterrupt:
        logger.info('server shutdown requested')

    except Exception as e:
        logger.error(f'server error: {e}')
        raise SystemExit(1)


if __name__ == '__main__':
    run()
