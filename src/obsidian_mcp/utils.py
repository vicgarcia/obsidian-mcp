from typing import Dict, List
import os
import re
from datetime import datetime
from pathlib import Path
import zoneinfo

import logging
logger = logging.getLogger(__name__)


def get_vault_base() -> Path:
    ''' Get the vault base path from environment variable. '''
    vault_path = os.getenv('OBSIDIAN_VAULT_PATH', '/vault')
    if not vault_path:
        logger.error("OBSIDIAN_VAULT_PATH environment variable is required")
        raise ValueError("OBSIDIAN_VAULT_PATH environment variable is required")

    resolved_path = Path(vault_path).resolve()
    logger.debug(f"vault base path: {resolved_path}")
    return resolved_path


def validate_vault_path(file_path: str) -> Path:
    ''' Validate and resolve a vault-relative path. '''
    vault_base = get_vault_base()
    vault_path = vault_base / Path(file_path)

    # security check: ensure path is within vault
    if not vault_path.is_relative_to(vault_base):
        logger.warning(f"path traversal attempt blocked: {file_path}")
        raise ValueError(f"Invalid path: {file_path} is outside vault directory")

    logger.debug(f"validated vault path: {vault_path}")
    return vault_path


def create_error_response(message: str) -> Dict[str, str]:
    ''' Create a standardized error response. '''
    return {"error": message}


def create_success_response() -> Dict[str, bool]:
    ''' Create a standardized success response. '''
    return {"success": True}


def create_file_info(path: Path, relative_to: Path) -> Dict[str, str]:
    ''' Create file information object with vault-relative path. '''
    relative_path = path.relative_to(relative_to)
    return {
        "path": str(relative_path).replace("\\", "/"),  # normalize path separators
        "name": path.name
    }


def get_local_datetime() -> datetime:
    ''' Get current datetime in local timezone, falling back to system timezone. '''
    try:
        # try to get timezone from environment variable
        tz_name = os.getenv('TZ')
        if tz_name:
            tz = zoneinfo.ZoneInfo(tz_name)
            logger.debug(f"using timezone from TZ env var: {tz_name}")
            return datetime.now(tz)

        # fall back to system local time
        logger.debug("using system local timezone")
        return datetime.now().astimezone()
    except Exception as e:
        # final fallback to naive datetime
        logger.warning(f"timezone detection failed, using naive datetime: {e}")
        return datetime.now()


def get_today_journal_path() -> str:
    '''
    Get today's journal entry path using local timezone.
    Returns path in format: journal/YYYY/MM/YYYY-MM-DD.md
    Month is always two digits with leading zero (e.g., "01", "10").
    '''
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
            # recursively list all files
            for item in directory.rglob("*"):
                if item.is_file():
                    files.append(create_file_info(item, vault_base))
        else:
            # list only direct files
            for item in directory.iterdir():
                if item.is_file():
                    files.append(create_file_info(item, vault_base))
        logger.debug(f"listed {len(files)} files in {directory} (recursive={recursive})")
    except PermissionError:
        # return empty list if we can't read the directory
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
        # return empty list if we can't read the directory
        logger.warning(f"permission denied reading directory: {directory}")
        pass

    return sorted(directories, key=lambda x: x["name"])


def is_valid_journal_filename(filename: str, year: str, month: str) -> bool:
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
