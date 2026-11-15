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
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# yaml frontmatter: a --- line at the very start, closed by the next --- (or ...) line
_FRONTMATTER = re.compile(r'\A---[ \t]*\r?\n(?:.*?\r?\n)??(?:---|\.\.\.)[ \t]*(?:\r?\n|\Z)', re.DOTALL)

# the section notes are added to through the day, and the file a day's notes start from
DAILY_NOTES_HEADING = '# Daily Notes'
DAILY_NOTES_SKELETON = f'\n\n{DAILY_NOTES_HEADING}\n'
_DAILY_NOTES = re.compile(r'^# Daily Notes[ \t]*\r?$', re.MULTILINE)


def _reason(error: Exception) -> str:
    '''
    Why an operation failed, without the file name.

    An OSError's text includes the absolute path (Permission denied: 'C:\\...'), so only
    its strerror goes into a VaultError; the full error is logged instead.
    '''
    return getattr(error, 'strerror', None) or type(error).__name__


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
            logger.error(f'vault directory does not exist: {self._vault_path}')
            raise VaultError('Vault directory does not exist')
        if not self._vault_path.is_dir():
            logger.error(f'vault path is not a directory: {self._vault_path}')
            raise VaultError('Vault path is not a directory')
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
            # newline='' writes \n as is; windows text mode would turn it into crlf
            vault_path.write_text(content, encoding='utf-8', newline='')
            logger.info(f'wrote file: {file_path} ({len(content)} chars)')
        except Exception as e:
            logger.error(f'failed to write file: {file_path}: {e}')
            raise VaultError(f'Failed to write file: {_reason(e)}', file_path)

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
            raise VaultError(f'Failed to create directory: {_reason(e)}', directory)

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
            date = self.get_local_datetime()
        return f'journal/{date.year}/{date.month:02d}/{date.year}-{date.month:02d}-{date.day:02d}.md'

    def get_local_datetime(self) -> datetime:
        '''
        Get current datetime in local timezone.

        datetime.now() can't be trusted when TZ is set: the Windows C runtime misreads
        names like America/New_York and runs hours off, so TZ always goes through zoneinfo.
        '''
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

    def read_journal_entry(self, date: datetime) -> Dict[str, Any]:
        '''
        Read the journal entry for a date.

        Args:
            date: Date of the journal entry

        Returns:
            Dictionary with path, whether the entry exists, and its content (empty if missing)
        '''
        journal_path = self.get_journal_path(date)
        if not self.file_exists(journal_path):
            logger.info(f'no journal entry: {journal_path}')
            return {'path': journal_path, 'exists': False, 'content': ''}
        return {'path': journal_path, 'exists': True, 'content': self.read_file(journal_path)}

    def _journal_file(self, date: Optional[datetime]) -> Tuple[str, Path]:
        '''The vault-relative and full path of a journal entry.'''
        journal_path = self.get_journal_path(date)
        return journal_path, self._validate_path(journal_path)

    def _read_journal_text(self, journal_path: str, full_path: Path) -> str:
        '''A journal file's exact text, line endings included, or '' if it doesn't exist.'''
        if not full_path.exists():
            return ''
        try:
            with open(full_path, 'r', encoding='utf-8', newline='') as f:
                return f.read()
        except UnicodeDecodeError:
            raise VaultError('Cannot read binary file', journal_path)

    def append_to_journal(self, text: str, date: Optional[datetime] = None) -> Dict[str, Any]:
        '''
        Append text to the end of a journal entry exactly as given, creating it if needed.

        Nothing is added, trimmed or converted: no separator, no trailing newline, no
        line ending translation. Existing content is never rewritten.

        Args:
            text: Text to append
            date: Date of the journal entry. Defaults to today.

        Returns:
            Dictionary with the entry path and whether the file was created

        Raises:
            VaultError: If the append fails
        '''
        journal_path, full_path = self._journal_file(date)
        created = not full_path.exists()

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'a', encoding='utf-8', newline='') as f:
                f.write(text)
            logger.info(f'appended to journal: {journal_path} ({len(text)} chars, created={created})')
        except OSError as e:
            logger.error(f'failed to append to journal: {journal_path}: {e}')
            raise VaultError(f'Failed to append to journal: {_reason(e)}', journal_path)

        return {'path': journal_path, 'created': created}

    def prepend_to_journal(self, text: str, date: Optional[datetime] = None) -> Dict[str, Any]:
        '''
        Insert text at the top of a journal entry exactly as given, creating it if needed.

        YAML frontmatter (a --- block on the first line, shown by Obsidian as properties)
        stays first and the text goes right after its closing --- line. Nothing else is
        added, trimmed or converted; the one exception is a newline after a closing ---
        that ends the file, so the text doesn't join the frontmatter.

        Args:
            text: Text to prepend
            date: Date of the journal entry. Defaults to today.

        Returns:
            Dictionary with the entry path and whether the file was created

        Raises:
            VaultError: If the prepend fails
        '''
        journal_path, full_path = self._journal_file(date)
        created = not full_path.exists()

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            existing = self._read_journal_text(journal_path, full_path)

            match = _FRONTMATTER.match(existing)
            frontmatter = match.group(0) if match else ''
            rest = existing[len(frontmatter):]
            if frontmatter and not frontmatter.endswith('\n'):
                frontmatter += '\n'

            with open(full_path, 'w', encoding='utf-8', newline='') as f:
                f.write(frontmatter + text + rest)
            logger.info(f'prepended to journal: {journal_path} ({len(text)} chars, created={created})')
        except OSError as e:
            logger.error(f'failed to prepend to journal: {journal_path}: {e}')
            raise VaultError(f'Failed to prepend to journal: {_reason(e)}', journal_path)

        return {'path': journal_path, 'created': created}

    def add_note_to_journal(self, text: str, date: Optional[datetime] = None) -> Dict[str, Any]:
        '''
        Append a note to the Daily Notes section of a journal entry, stamped with the time.

        A missing, empty or whitespace-only file becomes the daily notes skeleton first.
        A file without a # Daily Notes line gets one appended, after a blank line. A file
        that doesn't end in a newline gets one, so the note starts on its own line. The
        note is then appended as: text, newline, YYYY-MM-DD HH:MM, two newlines. The
        timestamp is always the current local time, even when date is an earlier day.

        Args:
            text: The note, starting with a ### heading, with no trailing newline
            date: Date of the journal entry. Defaults to today.

        Returns:
            Dictionary with the entry path, whether the file was created, and the timestamp

        Raises:
            VaultError: If the write fails
        '''
        journal_path, full_path = self._journal_file(date)
        created = not full_path.exists()
        timestamp = self.get_local_datetime().strftime('%Y-%m-%d %H:%M')
        note = f'{text}\n{timestamp}\n\n'

        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            existing = self._read_journal_text(journal_path, full_path)

            if not existing.strip():
                mode, lead = 'w', DAILY_NOTES_SKELETON
            elif not _DAILY_NOTES.search(existing):
                if existing.endswith('\n\n'):
                    gap = ''
                elif existing.endswith('\n'):
                    gap = '\n'
                else:
                    gap = '\n\n'
                mode, lead = 'a', f'{gap}{DAILY_NOTES_HEADING}\n'
            elif not existing.endswith('\n'):
                mode, lead = 'a', '\n'
            else:
                mode, lead = 'a', ''

            with open(full_path, mode, encoding='utf-8', newline='') as f:
                f.write(lead + note)
            logger.info(f'added note to journal: {journal_path} ({len(text)} chars, created={created})')
        except OSError as e:
            logger.error(f'failed to add note to journal: {journal_path}: {e}')
            raise VaultError(f'Failed to add note to journal: {_reason(e)}', journal_path)

        return {'path': journal_path, 'created': created, 'timestamp': timestamp}

    def write_journal_entry(self, content: str, date: Optional[datetime] = None) -> Dict[str, Any]:
        '''
        Replace the whole content of a journal entry, creating it if needed.

        Args:
            content: Full content of the entry
            date: Date of the journal entry. Defaults to today.

        Returns:
            Dictionary with the entry path and whether the file was created

        Raises:
            VaultError: If the write fails
        '''
        journal_path = self.get_journal_path(date)
        created = not self.file_exists(journal_path)
        self.write_file(journal_path, content)
        return {'path': journal_path, 'created': created}

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
