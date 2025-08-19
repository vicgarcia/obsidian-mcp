"""Utility functions for the Obsidian MCP server."""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import zoneinfo


def get_vault_base() -> Path:
    """Get the vault base path from environment variable."""
    vault_path = os.getenv('OBSIDIAN_VAULT_PATH', '/vault')
    if not vault_path:
        raise ValueError("OBSIDIAN_VAULT_PATH environment variable is required")

    return Path(vault_path).resolve()


def validate_vault_path(file_path: str) -> Path:
    """Validate and resolve a vault-relative path."""
    vault_base = get_vault_base()
    vault_path = vault_base / Path(file_path)

    # Security check: ensure path is within vault
    if not vault_path.is_relative_to(vault_base):
        raise ValueError(f"Invalid path: {file_path} is outside vault directory")

    return vault_path


def create_error_response(message: str) -> Dict[str, str]:
    """Create a standardized error response."""
    return {"error": message}


def create_success_response() -> Dict[str, bool]:
    """Create a standardized success response."""
    return {"success": True}


def create_file_info(path: Path, relative_to: Path) -> Dict[str, str]:
    """Create file information object with vault-relative path."""
    relative_path = path.relative_to(relative_to)
    return {
        "path": str(relative_path).replace("\\", "/"),  # Normalize path separators
        "name": path.name
    }


def get_local_datetime() -> datetime:
    """Get current datetime in local timezone, falling back to system timezone."""
    try:
        # Try to get timezone from environment variable
        tz_name = os.getenv('TZ')
        if tz_name:
            tz = zoneinfo.ZoneInfo(tz_name)
            return datetime.now(tz)
        
        # Fall back to system local time
        return datetime.now().astimezone()
    except Exception:
        # Final fallback to naive datetime
        return datetime.now()


def get_today_date_string() -> str:
    """Get today's date in YYYY-MM-DD format using local timezone."""
    return get_local_datetime().strftime("%Y-%m-%d")


def get_today_journal_path() -> str:
    """Get today's journal entry path using local timezone."""
    today = get_local_datetime()
    return f"journal/{today.year}/{today.month:02d}/{today.year}-{today.month:02d}-{today.day:02d}.md"


def list_files_in_directory(directory: Path, vault_base: Path, recursive: bool = False) -> List[Dict[str, str]]:
    """List files in a directory with vault-relative paths."""
    files = []

    if not directory.exists():
        return files

    try:
        if recursive:
            # Recursively list all files
            for item in directory.rglob("*"):
                if item.is_file():
                    files.append(create_file_info(item, vault_base))
        else:
            # List only direct files
            for item in directory.iterdir():
                if item.is_file():
                    files.append(create_file_info(item, vault_base))
    except PermissionError:
        # Return empty list if we can't read the directory
        pass

    return sorted(files, key=lambda x: x["name"])


def list_directories_in_directory(directory: Path, vault_base: Path) -> List[Dict[str, str]]:
    """List subdirectories in a directory with vault-relative paths."""
    directories = []

    if not directory.exists():
        return directories

    try:
        for item in directory.iterdir():
            if item.is_dir():
                directories.append(create_file_info(item, vault_base))
    except PermissionError:
        # Return empty list if we can't read the directory
        pass

    return sorted(directories, key=lambda x: x["name"])