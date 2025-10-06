''' Main MCP server implementation for Obsidian vault access. '''

import re
import sys
from typing import Dict, Any, List
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from .utils import (
    get_vault_base,
    validate_vault_path,
    create_error_response,
    create_success_response,
    get_today_journal_path,
    list_files_in_directory
)
from .models import FilePathInput, FileWriteInput, YearMonthInput


# initialize the MCP server
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
    Get today's journal entry path.

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

    Args:
        year: Year in YYYY format
        month: Month in MM format

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


def main():
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


if __name__ == "__main__":
    main()
