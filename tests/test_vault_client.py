'''
Tests for the VaultClient class.
'''

import pytest
from datetime import datetime
from pathlib import Path

from obsidian_mcp.vault_client import VaultClient, VaultError


class TestVaultClientInit:
    '''Test VaultClient initialization.'''

    def test_context_manager_valid_vault(self, vault_path):
        '''Test context manager with valid vault.'''
        with VaultClient(str(vault_path)) as vault:
            assert vault.vault_path == vault_path.resolve()

    def test_context_manager_nonexistent_vault(self, tmp_path):
        '''Test context manager with nonexistent vault.'''
        with pytest.raises(VaultError, match='does not exist'):
            with VaultClient(str(tmp_path / 'nonexistent')):
                pass

    def test_context_manager_file_not_directory(self, tmp_path):
        '''Test context manager with file instead of directory.'''
        test_file = tmp_path / 'test.txt'
        test_file.write_text('test')
        with pytest.raises(VaultError, match='not a directory'):
            with VaultClient(str(test_file)):
                pass


class TestFileOperations:
    '''Test VaultClient file operations.'''

    def test_read_existing_file(self, vault_path):
        '''Test reading an existing file.'''
        with VaultClient(str(vault_path)) as vault:
            content = vault.read_file('journal/2025/01/2025-01-15.md')
            assert 'January 15, 2025' in content
            assert '#journal' in content

    def test_read_nonexistent_file(self, vault_path):
        '''Test reading a non-existent file.'''
        with VaultClient(str(vault_path)) as vault:
            with pytest.raises(VaultError, match='File not found'):
                vault.read_file('nonexistent/file.md')

    def test_read_directory_as_file(self, vault_path):
        '''Test reading a directory as a file.'''
        with VaultClient(str(vault_path)) as vault:
            with pytest.raises(VaultError, match='not a file'):
                vault.read_file('journal')

    def test_read_path_traversal(self, vault_path):
        '''Test that path traversal is blocked.'''
        with VaultClient(str(vault_path)) as vault:
            with pytest.raises(VaultError, match='outside vault'):
                vault.read_file('../../../etc/passwd')

    def test_write_new_file(self, vault_path):
        '''Test writing a new file.'''
        test_content = '# Test Note\n\nThis is test content.'
        with VaultClient(str(vault_path)) as vault:
            vault.write_file('test_write/new_file.md', test_content)

            test_file = vault_path / 'test_write' / 'new_file.md'
            assert test_file.exists()
            assert test_file.read_text() == test_content

    def test_write_creates_directories(self, vault_path):
        '''Test that write_file creates parent directories.'''
        test_content = '# Deep Test\n\nNested content.'
        with VaultClient(str(vault_path)) as vault:
            vault.write_file('deep_test/nested/path/test.md', test_content)

            test_file = vault_path / 'deep_test' / 'nested' / 'path' / 'test.md'
            assert test_file.exists()
            assert test_file.parent.exists()

    def test_file_exists_true(self, vault_path):
        '''Test file_exists returns True for existing file.'''
        with VaultClient(str(vault_path)) as vault:
            assert vault.file_exists('journal/2025/01/2025-01-15.md') is True

    def test_file_exists_false(self, vault_path):
        '''Test file_exists returns False for non-existent file.'''
        with VaultClient(str(vault_path)) as vault:
            assert vault.file_exists('nonexistent.md') is False


class TestDirectoryOperations:
    '''Test VaultClient directory operations.'''

    def test_list_files_existing(self, vault_path):
        '''Test listing files in an existing directory.'''
        with VaultClient(str(vault_path)) as vault:
            files = vault.list_files('journal/2025/01')
            assert len(files) > 0
            assert any(f['name'] == '2025-01-15.md' for f in files)

    def test_list_files_nonexistent(self, vault_path):
        '''Test listing files in a non-existent directory.'''
        with VaultClient(str(vault_path)) as vault:
            files = vault.list_files('nonexistent')
            assert files == []

    def test_list_files_recursive(self, vault_path):
        '''Test recursive file listing.'''
        with VaultClient(str(vault_path)) as vault:
            files = vault.list_files('journal', recursive=True)
            assert len(files) > 0
            assert any('2025/01' in f['path'] for f in files)

    def test_list_directories(self, vault_path):
        '''Test listing directories.'''
        (vault_path / 'projects' / 'test-project-1').mkdir(parents=True, exist_ok=True)
        (vault_path / 'projects' / 'test-project-2').mkdir(parents=True, exist_ok=True)

        with VaultClient(str(vault_path)) as vault:
            dirs = vault.list_directories('projects')
            dir_names = [d['name'] for d in dirs]
            assert 'test-project-1' in dir_names
            assert 'test-project-2' in dir_names

    def test_create_directory(self, vault_path):
        '''Test creating a directory.'''
        with VaultClient(str(vault_path)) as vault:
            vault.create_directory('new_test_dir/nested')
            assert (vault_path / 'new_test_dir' / 'nested').exists()

    def test_directory_exists_true(self, vault_path):
        '''Test directory_exists returns True for existing directory.'''
        with VaultClient(str(vault_path)) as vault:
            assert vault.directory_exists('journal') is True

    def test_directory_exists_false(self, vault_path):
        '''Test directory_exists returns False for non-existent directory.'''
        with VaultClient(str(vault_path)) as vault:
            assert vault.directory_exists('nonexistent_dir') is False


class TestJournalOperations:
    '''Test VaultClient journal operations.'''

    def test_get_journal_path_today(self, vault_path):
        '''Test getting today's journal path.'''
        with VaultClient(str(vault_path)) as vault:
            path = vault.get_journal_path()
            assert path.startswith('journal/')
            assert path.endswith('.md')
            today = datetime.now()
            assert str(today.year) in path

    def test_get_journal_path_specific_date(self, vault_path):
        '''Test getting journal path for a specific date.'''
        specific_date = datetime(2025, 3, 15)
        with VaultClient(str(vault_path)) as vault:
            path = vault.get_journal_path(specific_date)
            assert path == 'journal/2025/03/2025-03-15.md'

    def test_is_valid_journal_filename_valid(self, vault_path):
        '''Test valid journal filename.'''
        with VaultClient(str(vault_path)) as vault:
            assert vault.is_valid_journal_filename('2025-01-15.md', '2025', '01') is True

    def test_is_valid_journal_filename_invalid(self, vault_path):
        '''Test invalid journal filename.'''
        with VaultClient(str(vault_path)) as vault:
            assert vault.is_valid_journal_filename('notes.md', '2025', '01') is False
            assert vault.is_valid_journal_filename('2025-02-15.md', '2025', '01') is False

    def test_list_journal_entries(self, vault_path):
        '''Test listing journal entries.'''
        with VaultClient(str(vault_path)) as vault:
            entries = vault.list_journal_entries('2025', '01')
            assert len(entries) > 0
            assert any(e['name'] == '2025-01-15.md' for e in entries)


class TestProjectOperations:
    '''Test VaultClient project operations.'''

    def test_list_projects(self, vault_path):
        '''Test listing projects.'''
        (vault_path / 'projects' / 'project-a').mkdir(parents=True, exist_ok=True)
        (vault_path / 'projects' / 'project-b').mkdir(parents=True, exist_ok=True)

        with VaultClient(str(vault_path)) as vault:
            projects = vault.list_projects()
            project_names = [p['name'] for p in projects]
            assert 'project-a' in project_names
            assert 'project-b' in project_names

    def test_list_project_content(self, vault_path):
        '''Test listing project content.'''
        project_dir = vault_path / 'projects' / 'test-list-content'
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / 'readme.md').write_text('# README')
        (project_dir / 'notes.md').write_text('# Notes')

        with VaultClient(str(vault_path)) as vault:
            files = vault.list_project_content('test-list-content')
            file_names = [f['name'] for f in files]
            assert 'readme.md' in file_names
            assert 'notes.md' in file_names

    def test_list_project_content_nonexistent(self, vault_path):
        '''Test listing content of non-existent project.'''
        with VaultClient(str(vault_path)) as vault:
            with pytest.raises(VaultError, match='Project not found'):
                vault.list_project_content('nonexistent-project')

    def test_create_project(self, vault_path):
        '''Test creating a project.'''
        with VaultClient(str(vault_path)) as vault:
            vault.create_project('new-test-project')
            assert (vault_path / 'projects' / 'new-test-project').exists()


class TestWikiOperations:
    '''Test VaultClient wiki operations.'''

    def test_list_wiki_empty(self, vault_path):
        '''Test listing wiki when empty.'''
        wiki_dir = vault_path / 'wiki'
        wiki_dir.mkdir(parents=True, exist_ok=True)
        for f in wiki_dir.glob('*'):
            if f.is_file():
                f.unlink()

        with VaultClient(str(vault_path)) as vault:
            articles = vault.list_wiki()
            assert articles == []

    def test_list_wiki_with_articles(self, setup_wiki, vault_path):
        '''Test listing wiki with articles.'''
        with VaultClient(str(vault_path)) as vault:
            articles = vault.list_wiki()
            assert len(articles) == 3
            article_names = [a['name'] for a in articles]
            assert 'python-asyncio.md' in article_names
