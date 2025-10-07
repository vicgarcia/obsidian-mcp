import re
import sys
from typing import Dict, Any, List
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
)


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
        # validate input
        validated_input = FilePathInput(file_path=file_path)

        # validate and resolve vault path
        vault_path = validate_vault_path(validated_input.file_path)

        # check if file exists
        if not vault_path.exists():
            return create_error_response(f"File not found: {validated_input.file_path}")

        # check if it's actually a file
        if not vault_path.is_file():
            return create_error_response(f"Path is not a file: {validated_input.file_path}")

        # read file content
        try:
            # try to read as text file
            content = vault_path.read_text(encoding='utf-8')
            return {"content": content}
        except UnicodeDecodeError:
            # if it's a binary file, return error
            return create_error_response(f"Cannot read binary file: {validated_input.file_path}")

    except ValidationError as e:
        return create_error_response(f"Invalid input: {e}")
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response(f"Unexpected error reading file: {e}")


@mcp.tool()
def write_file(file_path: str, content: str) -> Dict[str, Any]:
    '''
    Write content to a file in the Obsidian vault.

    Args:
        file_path: Vault-relative path to the file
        content: Content to write to the file

    Returns:
        Dictionary with success indicator or error message
    '''
    try:
        # validate input
        validated_input = FileWriteInput(file_path=file_path, content=content)

        # validate and resolve vault path
        vault_path = validate_vault_path(validated_input.file_path)

        # create parent directories if they don't exist
        vault_path.parent.mkdir(parents=True, exist_ok=True)

        # write file content
        vault_path.write_text(validated_input.content, encoding='utf-8')

        return create_success_response()

    except ValidationError as e:
        return create_error_response(f"Invalid input: {e}")
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response(f"Unexpected error writing file: {e}")


@mcp.tool()
def list_todays_journal_entry() -> Dict[str, Any]:
    '''
    Get today's journal entry path in the format journal/YYYY/MM/YYYY-MM-DD.md.

    Returns:
        Dictionary with today's journal entry path and name
    '''
    try:
        journal_path = get_today_journal_path()

        # return the path info regardless of whether file exists
        return {
            "path": journal_path,
            "name": Path(journal_path).name
        }

    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
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
            if file_path.suffix == ".md" and _is_valid_journal_filename(file_path.name, validated_input.year, validated_input.month):
                journal_entries.append(file_info)

        return sorted(journal_entries, key=lambda x: x["name"])

    except ValidationError as e:
        return [create_error_response(f"Invalid input: {e}")]
    except ValueError as e:
        return [create_error_response(str(e))]
    except Exception as e:
        return [create_error_response(f"Unexpected error listing journal entries: {e}")]


def _is_valid_journal_filename(filename: str, year: str, month: str) -> bool:
    '''
    Check if a filename matches the expected journal entry format.

    Args:
        filename: The filename to check
        year: Expected year in YYYY format
        month: Expected month in MM format

    Returns:
        True if filename matches YYYY-MM-DD.md format for the given year/month
    '''
    # expected pattern: YYYY-MM-DD.md
    pattern = f"^{year}-{month}-\\d{{2}}\\.md$"
    return bool(re.match(pattern, filename))


@mcp.tool()
def list_projects() -> List[Dict[str, str]]:
    '''
    List all projects (subdirectories in the projects directory).

    Returns:
        List of project directories with metadata
    '''
    try:
        vault_base = get_vault_base()
        projects_dir = vault_base / "projects"

        # get all subdirectories in the projects directory
        projects = list_directories_in_directory(projects_dir, vault_base)

        return projects

    except ValueError as e:
        return [create_error_response(str(e))]
    except Exception as e:
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
        # validate input
        validated_input = ProjectInput(project=project)

        vault_base = get_vault_base()
        project_dir = vault_base / "projects" / validated_input.project

        # check if project directory exists
        if not project_dir.exists():
            return [create_error_response(f"Project not found: {validated_input.project}")]

        if not project_dir.is_dir():
            return [create_error_response(f"Project is not a directory: {validated_input.project}")]

        # get all files recursively in the project directory
        files = list_files_in_directory(project_dir, vault_base, recursive=True)

        return files

    except ValidationError as e:
        return [create_error_response(f"Invalid input: {e}")]
    except ValueError as e:
        return [create_error_response(str(e))]
    except Exception as e:
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
        # validate input
        validated_input = ProjectInput(project=project)

        vault_base = get_vault_base()
        project_dir = vault_base / "projects" / validated_input.project

        # create the directory (parents=True creates projects dir if it doesn't exist)
        project_dir.mkdir(parents=True, exist_ok=True)

        return create_success_response()

    except ValidationError as e:
        return create_error_response(f"Invalid input: {e}")
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response(f"Unexpected error creating project: {e}")


def run():
    ''' Main entry point for the MCP server. '''
    try:
        # validate that vault path is configured
        vault_base = get_vault_base()

        # ensure vault directory exists
        if not vault_base.exists():
            print(f"Error: Vault directory does not exist: {vault_base}", file=sys.stderr)
            sys.exit(1)

        if not vault_base.is_dir():
            print(f"Error: Vault path is not a directory: {vault_base}", file=sys.stderr)
            sys.exit(1)

        # run the server
        mcp.run()

    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
