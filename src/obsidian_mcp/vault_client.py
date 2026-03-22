'''
Vault client for Obsidian file system operations.

Provides a context manager interface for all vault operations including
file reading, writing, and directory management.
'''

import logging
import os
import re
import zoneinfo
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class VaultError(Exception):
    '''Exception raised for vault operation errors.'''

    def __init__(self, message: str, path: Optional[str] = None):
        self.message = message
        self.path = path
        super().__init__(message)

    def __str__(self) -> str:
        if self.path:
            return f'{self.message}: {self.path}'
        return self.message


class VaultClient:
    '''
    Client for Obsidian vault file system operations.

    Usage:
        with VaultClient('/path/to/vault') as vault:
            content = vault.read_file('journal/2025/01/2025-01-15.md')
            vault.write_file('notes/test.md', '# Test')
    '''

    def __init__(self, vault_path: str):
        '''
        Initialize the vault client.

        Args:
            vault_path: Path to the Obsidian vault directory
        '''
        self._vault_path = Path(vault_path).resolve()
        logger.debug(f'vault client initialized with path: {self._vault_path}')

    def __enter__(self) -> 'VaultClient':
        '''Enter context manager.'''
        if not self._vault_path.exists():
            raise VaultError('Vault directory does not exist', str(self._vault_path))
        if not self._vault_path.is_dir():
            raise VaultError('Vault path is not a directory', str(self._vault_path))
        logger.debug('vault client context entered')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        '''Exit context manager.'''
        logger.debug('vault client context exited')

    @property
    def vault_path(self) -> Path:
        '''Get the vault base path.'''
        return self._vault_path

    def _validate_path(self, file_path: str) -> Path:
        '''
        Validate and resolve a vault-relative path.

        Args:
            file_path: Vault-relative file path

        Returns:
            Resolved absolute Path

        Raises:
            VaultError: If path is outside vault directory
        '''
        full_path = self._vault_path / Path(file_path)
        if not full_path.resolve().is_relative_to(self._vault_path):
            logger.warning(f'path traversal attempt blocked: {file_path}')
            raise VaultError('Path is outside vault directory', file_path)
        return full_path.resolve()

    def _create_file_info(self, path: Path) -> Dict[str, str]:
        '''Create file information object with vault-relative path.'''
        relative_path = path.relative_to(self._vault_path)
        return {
            'path': str(relative_path).replace('\\', '/'),
            'name': path.name
        }

    # file operations

    def read_file(self, file_path: str) -> str:
        '''
        Read file content from the vault.

        Args:
            file_path: Vault-relative path to the file

        Returns:
            File content as string

        Raises:
            VaultError: If file not found, is not a file, or cannot be read
        '''
        vault_path = self._validate_path(file_path)

        if not vault_path.exists():
            logger.warning(f'file not found: {file_path}')
            raise VaultError('File not found', file_path)

        if not vault_path.is_file():
            logger.warning(f'path is not a file: {file_path}')
            raise VaultError('Path is not a file', file_path)

        try:
            content = vault_path.read_text(encoding='utf-8')
            logger.info(f'read file: {file_path} ({len(content)} chars)')
            return content
        except UnicodeDecodeError:
            logger.warning(f'cannot read binary file: {file_path}')
            raise VaultError('Cannot read binary file', file_path)

    def write_file(self, file_path: str, content: str) -> None:
        '''
        Write content to a file in the vault.

        Creates parent directories if they don't exist.

        Args:
            file_path: Vault-relative path to the file
            content: Content to write

        Raises:
            VaultError: If write operation fails
        '''
        vault_path = self._validate_path(file_path)

        try:
            vault_path.parent.mkdir(parents=True, exist_ok=True)
            vault_path.write_text(content, encoding='utf-8')
            logger.info(f'wrote file: {file_path} ({len(content)} chars)')
        except Exception as e:
            logger.error(f'failed to write file: {file_path}: {e}')
            raise VaultError(f'Failed to write file: {e}', file_path)

    def file_exists(self, file_path: str) -> bool:
        '''Check if a file exists in the vault.'''
        try:
            vault_path = self._validate_path(file_path)
            return vault_path.exists() and vault_path.is_file()
        except VaultError:
            return False

    # directory operations

    def list_files(self, directory: str, recursive: bool = False) -> List[Dict[str, str]]:
        '''
        List files in a directory with vault-relative paths.

        Args:
            directory: Vault-relative directory path
            recursive: If True, list files recursively

        Returns:
            List of file info dictionaries with 'path' and 'name' keys
        '''
        dir_path = self._validate_path(directory)

        if not dir_path.exists():
            logger.debug(f'directory does not exist: {directory}')
            return []

        files = []
        try:
            if recursive:
                for item in dir_path.rglob('*'):
                    if item.is_file():
                        files.append(self._create_file_info(item))
            else:
                for item in dir_path.iterdir():
                    if item.is_file():
                        files.append(self._create_file_info(item))
            logger.debug(f'listed {len(files)} files in {directory} (recursive={recursive})')
        except PermissionError:
            logger.warning(f'permission denied reading directory: {directory}')

        return sorted(files, key=lambda x: x['name'])

    def list_directories(self, directory: str) -> List[Dict[str, str]]:
        '''
        List subdirectories in a directory with vault-relative paths.

        Args:
            directory: Vault-relative directory path

        Returns:
            List of directory info dictionaries with 'path' and 'name' keys
        '''
        dir_path = self._validate_path(directory)

        if not dir_path.exists():
            logger.debug(f'directory does not exist: {directory}')
            return []

        directories = []
        try:
            for item in dir_path.iterdir():
                if item.is_dir():
                    directories.append(self._create_file_info(item))
            logger.debug(f'listed {len(directories)} directories in {directory}')
        except PermissionError:
            logger.warning(f'permission denied reading directory: {directory}')

        return sorted(directories, key=lambda x: x['name'])

    def create_directory(self, directory: str) -> None:
        '''
        Create a directory in the vault.

        Args:
            directory: Vault-relative directory path to create

        Raises:
            VaultError: If directory creation fails
        '''
        dir_path = self._validate_path(directory)

        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f'created directory: {directory}')
        except Exception as e:
            logger.error(f'failed to create directory: {directory}: {e}')
            raise VaultError(f'Failed to create directory: {e}', directory)

    def directory_exists(self, directory: str) -> bool:
        '''Check if a directory exists in the vault.'''
        try:
            dir_path = self._validate_path(directory)
            return dir_path.exists() and dir_path.is_dir()
        except VaultError:
            return False

    # journal operations

    def get_journal_path(self, date: Optional[datetime] = None) -> str:
        '''
        Get the journal entry path for a date.

        Args:
            date: Date for the journal entry. Defaults to today.

        Returns:
            Journal path in format: journal/YYYY/MM/YYYY-MM-DD.md
        '''
        if date is None:
            date = self._get_local_datetime()
        return f'journal/{date.year}/{date.month:02d}/{date.year}-{date.month:02d}-{date.day:02d}.md'

    def _get_local_datetime(self) -> datetime:
        '''Get current datetime in local timezone.'''
        try:
            tz_name = os.getenv('TZ')
            if tz_name:
                tz = zoneinfo.ZoneInfo(tz_name)
                logger.debug(f'using timezone from TZ env var: {tz_name}')
                return datetime.now(tz)
            logger.debug('using system local timezone')
            return datetime.now().astimezone()
        except Exception as e:
            logger.warning(f'timezone detection failed, using naive datetime: {e}')
            return datetime.now()

    def is_valid_journal_filename(self, filename: str, year: str, month: str) -> bool:
        '''Check if a filename matches the expected journal entry format.'''
        pattern = f'^{year}-{month}-\\d{{2}}\\.md$'
        return bool(re.match(pattern, filename))

    def list_journal_entries(self, year: str, month: str) -> List[Dict[str, str]]:
        '''
        List journal entries for a specific year and month.

        Args:
            year: Year in YYYY format
            month: Month in MM format

        Returns:
            List of journal entry info dictionaries
        '''
        journal_dir = f'journal/{year}/{month}'
        files = self.list_files(journal_dir, recursive=False)

        entries = []
        for file_info in files:
            file_path = Path(file_info['path'])
            if file_path.suffix == '.md' and self.is_valid_journal_filename(file_path.name, year, month):
                entries.append(file_info)

        logger.info(f'found {len(entries)} journal entries for {year}/{month}')
        return sorted(entries, key=lambda x: x['name'])

    # project operations

    def list_projects(self) -> List[Dict[str, str]]:
        '''
        List all projects (subdirectories in the projects directory).

        Returns:
            List of project directory info dictionaries
        '''
        projects = self.list_directories('projects')
        logger.info(f'found {len(projects)} projects')
        return projects

    def list_project_content(self, project: str) -> List[Dict[str, str]]:
        '''
        List all files within a project.

        Args:
            project: Name of the project directory

        Returns:
            List of file info dictionaries

        Raises:
            VaultError: If project not found or is not a directory
        '''
        project_path = f'projects/{project}'

        if not self.directory_exists(project_path):
            raise VaultError('Project not found', project)

        files = self.list_files(project_path, recursive=True)
        logger.info(f'found {len(files)} files in project: {project}')
        return files

    def create_project(self, project: str) -> None:
        '''
        Create a new project directory.

        Args:
            project: Name of the project directory to create

        Raises:
            VaultError: If project creation fails
        '''
        project_path = f'projects/{project}'
        self.create_directory(project_path)
        logger.info(f'created project: {project}')

    # wiki operations

    def list_wiki(self) -> List[Dict[str, str]]:
        '''
        List all wiki articles (markdown files in wiki directory).

        Returns:
            List of wiki article info dictionaries
        '''
        files = self.list_files('wiki', recursive=False)
        articles = [f for f in files if Path(f['path']).suffix == '.md']
        logger.info(f'found {len(articles)} wiki articles')
        return articles
