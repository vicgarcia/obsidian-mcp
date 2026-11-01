'''
Tests for MCP tools.
'''

import pytest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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

    @pytest.mark.parametrize('tz', ['Pacific/Kiritimati', 'Pacific/Pago_Pago'])
    def test_tz_decides_today_for_every_date_tool(self, monkeypatch, tz):
        '''These zones are 25 hours apart, so at least one differs from the system date.'''
        monkeypatch.setenv('TZ', tz)
        expected = datetime.now(ZoneInfo(tz))

        assert server.get_current_date()['formatted'] == expected.strftime('%Y-%m-%d')
        assert expected.strftime('%A %B %d, %Y') in server.start_daily_notes_session()
        assert expected.strftime('%Y-%m-%d') in server.list_todays_journal_entry()['path']

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

    def test_read_wiki_article(self, setup_wiki):
        '''Test that a path from list_wiki can be read.'''
        result = server.read_wiki_article('wiki/python-asyncio.md')
        assert result['content']

    @pytest.mark.parametrize('path', [
        'journal/2025/01/2025-01-15.md',
        'projects/scoped/plan.md',
        'wiki',
        'wiki/../journal/2025/01/2025-01-15.md',
    ])
    def test_read_wiki_article_refuses_paths_outside_the_wiki(self, setup_wiki, vault_path, path):
        (vault_path / 'projects' / 'scoped').mkdir(parents=True, exist_ok=True)
        (vault_path / 'projects' / 'scoped' / 'plan.md').write_text('private')

        result = server.read_wiki_article(path)
        assert result['success'] is False
        assert 'content' not in result


class TestProjectFileTools:
    '''Test that project file tools stay inside a project.'''

    @pytest.fixture
    def project(self, vault_path):
        project_dir = vault_path / 'projects' / 'scoped'
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / 'plan.md').write_text('shelves')
        return project_dir

    def test_read_project_file(self, project):
        assert server.read_project_file('projects/scoped/plan.md') == {'content': 'shelves'}

    def test_write_project_file_replaces_and_creates(self, project):
        assert server.write_project_file('projects/scoped/plan.md', 'more shelves') == {'success': True}
        assert (project / 'plan.md').read_text() == 'more shelves'
        assert server.write_project_file('projects/scoped/notes/new.md', 'hello') == {'success': True}
        assert (project / 'notes' / 'new.md').read_text() == 'hello'

    @pytest.mark.parametrize('path', [
        'journal/2025/01/2025-01-15.md',
        'wiki/article.md',
        'notes.md',
        'projects/loose.md',
        'projects',
        'projects/scoped/../../journal/2025/01/2025-01-15.md',
        '/etc/passwd',
        'C:/Windows/system.ini',
    ])
    def test_paths_outside_a_project_are_refused(self, project, vault_path, path):
        before = sorted(str(p) for p in vault_path.rglob('*'))
        read = server.read_project_file(path)
        written = server.write_project_file(path, 'overwritten')

        assert read['success'] is False and 'content' not in read
        assert written['success'] is False
        assert sorted(str(p) for p in vault_path.rglob('*')) == before

    def test_write_refuses_to_create_a_project(self, project, vault_path):
        result = server.write_project_file('projects/typo/plan.md', 'hello')
        assert result['success'] is False
        assert 'Project not found' in result['error']
        assert not (vault_path / 'projects' / 'typo').exists()

    def test_write_does_not_change_a_journal_entry(self, project, vault_path):
        entry = vault_path / 'journal' / '2025' / '01' / '2025-01-15.md'
        before = entry.read_text()
        server.write_project_file('journal/2025/01/2025-01-15.md', 'overwritten')
        assert entry.read_text() == before


class TestJournalEntryTools:
    '''Test reading journal entries by date and appending to today's entry.'''

    def test_read_journal_entry(self):
        result = server.read_journal_entry('2025-01-15')
        assert result['exists'] is True
        assert 'January 15, 2025' in result['content']

    def test_read_journal_entry_missing(self):
        result = server.read_journal_entry('2025-01-16')
        assert result['exists'] is False
        assert result['content'] == ''

    @pytest.mark.parametrize('bad', ['2025-1-15', '2025-02-30', 'yesterday', '', '../2025-01-15'])
    def test_read_journal_entry_rejects_bad_dates(self, bad):
        result = server.read_journal_entry(bad)
        assert result['success'] is False
        assert 'Invalid input' in result['error']

    def test_append_to_todays_journal(self, vault_path):
        result = server.append_to_todays_journal('  remember the milk  ')
        assert result['success'] is True
        assert result['created'] is True
        assert (vault_path / result['path']).read_text() == 'remember the milk\n'

        again = server.append_to_todays_journal('and eggs')
        assert again['created'] is False
        assert (vault_path / result['path']).read_text() == 'remember the milk\n\nand eggs\n'

    def test_append_to_todays_journal_rejects_empty_text(self):
        result = server.append_to_todays_journal('   ')
        assert result['success'] is False
        assert 'Invalid input' in result['error']
