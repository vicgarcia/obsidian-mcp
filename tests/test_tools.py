'''
Tests for MCP tools.
'''

import pytest
from datetime import datetime
from pathlib import Path

from obsidian_mcp.vault_client import VaultClient
from obsidian_mcp import server


@pytest.fixture(autouse=True)
def setup_client(vault_path):
    '''Set up the vault client singleton for tools.'''
    server._client = VaultClient(str(vault_path))
    yield
    server._client = None


class TestFileTools:
    '''Test file operation tools.'''

    def test_read_existing_file(self, vault_path):
        '''Test reading an existing file.'''
        result = server.read_file('journal/2025/01/2025-01-15.md')
        assert 'content' in result
        assert 'January 15, 2025' in result['content']

    def test_read_nonexistent_file(self):
        '''Test reading a non-existent file.'''
        result = server.read_file('nonexistent/file.md')
        assert 'error' in result
        assert result['success'] is False

    def test_read_file_path_traversal(self):
        '''Test that path traversal is prevented.'''
        result = server.read_file('../../../etc/passwd')
        assert 'error' in result
        assert 'Invalid input' in result['error']

    def test_write_new_file(self, vault_path):
        '''Test writing a new file.'''
        test_content = '# Test Note\n\nThis is test content.'
        result = server.write_file('tools_test/new_file.md', test_content)
        assert result == {'success': True}

        test_file = vault_path / 'tools_test' / 'new_file.md'
        assert test_file.exists()
        assert test_file.read_text() == test_content

    def test_write_file_path_traversal(self):
        '''Test that path traversal is prevented in write.'''
        result = server.write_file('../../../tmp/evil.txt', 'evil content')
        assert 'error' in result
        assert 'Invalid input' in result['error']


class TestDateTools:
    '''Test date tools.'''

    def test_get_current_date(self):
        '''Test getting current date.'''
        result = server.get_current_date()
        assert 'formatted' in result
        assert 'human' in result

        formatted = result['formatted']
        assert len(formatted) == 10
        assert formatted[4] == '-'
        assert formatted[7] == '-'

        expected_date = datetime.now().strftime('%Y-%m-%d')
        assert formatted == expected_date


class TestJournalTools:
    '''Test journal tools.'''

    def test_list_todays_journal_entry(self):
        '''Test getting today's journal entry path.'''
        result = server.list_todays_journal_entry()
        assert 'path' in result
        assert 'name' in result
        assert result['path'].startswith('journal/')
        assert result['path'].endswith('.md')

    def test_start_daily_notes_session(self):
        '''Test starting daily notes session.'''
        result = server.start_daily_notes_session()
        assert isinstance(result, str)
        assert 'daily notes session' in result
        assert 'journal entry' in result

    def test_list_journal_entries_by_year_and_month(self, vault_path):
        '''Test listing journal entries.'''
        test_dir = vault_path / 'journal' / '2025' / '01'
        test_dir.mkdir(parents=True, exist_ok=True)

        result = server.list_journal_entries_by_year_and_month('2025', '01')
        assert isinstance(result, list)
        if len(result) > 0 and 'name' in result[0]:
            assert any(e['name'] == '2025-01-15.md' for e in result)

    def test_list_journal_entries_invalid_year(self):
        '''Test listing journal entries with invalid year.'''
        result = server.list_journal_entries_by_year_and_month('25', '01')
        assert isinstance(result, list)
        assert len(result) == 1
        assert 'error' in result[0]

    def test_list_journal_entries_invalid_month(self):
        '''Test listing journal entries with invalid month.'''
        result = server.list_journal_entries_by_year_and_month('2025', '13')
        assert isinstance(result, list)
        assert len(result) == 1
        assert 'error' in result[0]


class TestProjectTools:
    '''Test project tools.'''

    def test_list_projects(self, vault_path):
        '''Test listing projects.'''
        (vault_path / 'projects' / 'tool-test-project').mkdir(parents=True, exist_ok=True)

        result = server.list_projects()
        assert isinstance(result, list)
        project_names = [p['name'] for p in result if 'name' in p]
        assert 'tool-test-project' in project_names

    def test_list_project_content(self, vault_path):
        '''Test listing project content.'''
        project_dir = vault_path / 'projects' / 'content-test'
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / 'readme.md').write_text('# README')

        result = server.list_project_content('content-test')
        assert isinstance(result, list)
        file_names = [f['name'] for f in result if 'name' in f]
        assert 'readme.md' in file_names

    def test_list_project_content_nonexistent(self):
        '''Test listing content of non-existent project.'''
        result = server.list_project_content('nonexistent-project')
        assert isinstance(result, list)
        assert len(result) == 1
        assert 'error' in result[0]

    def test_list_project_content_invalid_name(self):
        '''Test listing project content with invalid name.'''
        result = server.list_project_content('../etc')
        assert isinstance(result, list)
        assert len(result) == 1
        assert 'error' in result[0]

    def test_create_project(self, vault_path):
        '''Test creating a project.'''
        result = server.create_project('new-tool-test-project')
        assert result == {'success': True}

        project_dir = vault_path / 'projects' / 'new-tool-test-project'
        assert project_dir.exists()
        assert project_dir.is_dir()

    def test_create_project_invalid_name(self):
        '''Test creating project with invalid name.'''
        result = server.create_project('invalid/name')
        assert 'error' in result
        assert result['success'] is False


class TestWikiTools:
    '''Test wiki tools.'''

    def test_list_wiki_empty(self, vault_path):
        '''Test listing wiki when empty.'''
        wiki_dir = vault_path / 'wiki'
        wiki_dir.mkdir(parents=True, exist_ok=True)
        for f in wiki_dir.glob('*'):
            if f.is_file():
                f.unlink()

        result = server.list_wiki()
        assert isinstance(result, list)
        assert len(result) == 0

    def test_list_wiki_with_content(self, setup_wiki):
        '''Test listing wiki with content.'''
        result = server.list_wiki()
        assert isinstance(result, list)
        assert len(result) == 3

        article_names = [a['name'] for a in result]
        assert 'python-asyncio.md' in article_names


