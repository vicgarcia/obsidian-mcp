from typing import Dict, Any, List
import os
import sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from .models import (
    FilePathInput,
    FileWriteInput,
    YearMonthInput,
    ProjectInput,
)
from .utils import (
    get_vault_base,
    validate_vault_path,
    create_error_response,
    create_success_response,
    get_today_journal_path,
    list_files_in_directory,
    list_directories_in_directory,
    is_valid_journal_filename,
)

import logging
logger = logging.getLogger(__name__)

mcp = FastMCP("Obsidian MCP Server")


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
        # validate input
        validated_input = FilePathInput(file_path=file_path)

        # validate and resolve vault path
        vault_path = validate_vault_path(validated_input.file_path)

        # check if file exists
        if not vault_path.exists():
            logger.warning(f"file not found: {validated_input.file_path}")
            return create_error_response(f"File not found: {validated_input.file_path}")

        # check if it's actually a file
        if not vault_path.is_file():
            logger.warning(f"path is not a file: {validated_input.file_path}")
            return create_error_response(f"Path is not a file: {validated_input.file_path}")

        # read file content
        try:
            # try to read as text file
            content = vault_path.read_text(encoding='utf-8')
            logger.info(f"successfully read file: {validated_input.file_path} ({len(content)} chars)")
            return {"content": content}
        except UnicodeDecodeError:
            # if it's a binary file, return error
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
        # validate input
        validated_input = FileWriteInput(file_path=file_path, content=content)

        # validate and resolve vault path
        vault_path = validate_vault_path(validated_input.file_path)

        # create parent directories if they don't exist
        vault_path.parent.mkdir(parents=True, exist_ok=True)

        # write file content
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

        # return the path info regardless of whether file exists
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
        # validate input
        validated_input = YearMonthInput(year=year, month=month)

        vault_base = get_vault_base()
        journal_dir = vault_base / "journal" / validated_input.year / validated_input.month

        # get all files in the journal directory
        files = list_files_in_directory(journal_dir, vault_base)

        # filter for markdown files with correct date format
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

    Returns:
        List of project directories with metadata
    '''
    try:
        logger.debug("list_projects called")
        vault_base = get_vault_base()
        projects_dir = vault_base / "projects"

        # get all subdirectories in the projects directory
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
        # validate input
        validated_input = ProjectInput(project=project)

        vault_base = get_vault_base()
        project_dir = vault_base / "projects" / validated_input.project

        # check if project directory exists
        if not project_dir.exists():
            logger.warning(f"project not found: {validated_input.project}")
            return [create_error_response(f"Project not found: {validated_input.project}")]

        if not project_dir.is_dir():
            logger.warning(f"project is not a directory: {validated_input.project}")
            return [create_error_response(f"Project is not a directory: {validated_input.project}")]

        # get all files recursively in the project directory
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
        # validate input
        validated_input = ProjectInput(project=project)

        vault_base = get_vault_base()
        project_dir = vault_base / "projects" / validated_input.project

        # create the directory (parents=True creates projects dir if it doesn't exist)
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
def list_knowledge_guides() -> List[Dict[str, str]]:
    '''
    List all knowledge guides (markdown files in the knowledge directory).

    Knowledge guides are complete, standalone documentation on specific topics.
    Use descriptive filenames that clearly indicate content (e.g., 'python-asyncio.md',
    'docker-networking.md', 'git-workflows.md').

    The knowledge directory uses a flat structure - all guides live directly in
    knowledge/*.md with no subdirectories. This keeps discovery simple.

    Returns:
        List of guide files with metadata, sorted alphabetically
    '''
    try:
        logger.debug("list_knowledge_guides called")
        vault_base = get_vault_base()
        knowledge_dir = vault_base / "knowledge"

        # get all files in the knowledge directory (non-recursive)
        files = list_files_in_directory(knowledge_dir, vault_base, recursive=False)

        # filter to markdown files only
        guides = [f for f in files if Path(f["path"]).suffix == ".md"]

        logger.info(f"found {len(guides)} knowledge guides")
        return guides

    except ValueError as e:
        logger.error(f"value error listing knowledge guides: {e}")
        return [create_error_response(str(e))]
    except Exception as e:
        logger.exception(f"unexpected error listing knowledge guides: {e}")
        return [create_error_response(f"Unexpected error listing knowledge guides: {e}")]


def run():
    ''' Main entry point for the MCP server. '''
    # configure logging
    logging.basicConfig(
        level=logging.DEBUG if os.getenv('LOG_LEVEL', 'info').lower() == 'debug' else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )

    try:
        logger.info("starting obsidian MCP server")

        # validate that vault path is configured
        vault_base = get_vault_base()
        logger.info(f"vault path configured: {vault_base}")

        # ensure vault directory exists
        if not vault_base.exists():
            logger.error(f"vault directory does not exist: {vault_base}")
            print(f"Error: Vault directory does not exist: {vault_base}", file=sys.stderr)
            sys.exit(1)

        if not vault_base.is_dir():
            logger.error(f"vault path is not a directory: {vault_base}")
            print(f"Error: Vault path is not a directory: {vault_base}", file=sys.stderr)
            sys.exit(1)

        logger.info("vault validation successful, starting server")
        # run the server
        mcp.run()

    except ValueError as e:
        logger.exception(f"configuration error: {e}")
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.exception(f"unexpected error: {e}")
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
