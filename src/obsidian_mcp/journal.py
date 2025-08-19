"""Journal section tools for the Obsidian MCP server."""

from typing import Dict, Any, List
from pathlib import Path

from pydantic import ValidationError

from .utils import (
    get_vault_base,
    create_error_response,
    create_file_info,
    get_today_journal_path,
    list_files_in_directory
)
from .models import YearMonthInput


def register_journal_tools(mcp):
    """Register journal-related tools with the MCP server."""
    
    @mcp.tool()
    def list_todays_journal_entry() -> Dict[str, Any]:
        """
        Get today's journal entry path.
        
        Returns:
            Dictionary with today's journal entry path and name
        """
        try:
            vault_base = get_vault_base()
            journal_path = get_today_journal_path()
            
            # Return the path info regardless of whether file exists
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
        """
        List all journal entries for a specific year and month.
        
        Args:
            year: Year in YYYY format
            month: Month in MM format
            
        Returns:
            List of journal entries with metadata
        """
        try:
            # Validate input
            validated_input = YearMonthInput(year=year, month=month)
            
            vault_base = get_vault_base()
            journal_dir = vault_base / "journal" / validated_input.year / validated_input.month
            
            # Get all files in the journal directory
            files = list_files_in_directory(journal_dir, vault_base)
            
            # Filter for markdown files with correct date format
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
    """
    Check if a filename matches the expected journal entry format.
    
    Args:
        filename: The filename to check
        year: Expected year in YYYY format
        month: Expected month in MM format
        
    Returns:
        True if filename matches YYYY-MM-DD.md format for the given year/month
    """
    import re
    
    # Expected pattern: YYYY-MM-DD.md
    pattern = f"^{year}-{month}-\\d{{2}}\\.md$"
    return bool(re.match(pattern, filename))