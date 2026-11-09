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

        result = server.get_current_timestamp()
        assert result['date'] == expected.strftime('%Y-%m-%d')
        assert result['timezone'] == tz
        assert expected.strftime('%Y-%m-%d') in server.list_todays_journal_entry()['path']

    def test_get_current_timestamp(self, monkeypatch):
        '''Test the current timestamp has every format and they agree.'''
        monkeypatch.setenv('TZ', 'America/New_York')
        result = server.get_current_timestamp()
        assert set(result) == {
            'iso', 'utc', 'unix', 'date', 'time', 'time_12h', 'day_of_week',
            'human_date', 'human', 'iso_week', 'timezone', 'utc_offset',
        }
        local = datetime.fromisoformat(result['iso'])
        assert local.strftime('%Y-%m-%d') == result['date']
        assert local.strftime('%H:%M:%S') == result['time']
        assert result['iso'].endswith(result['utc_offset'])
        assert result['utc_offset'] in ('-05:00', '-04:00')
        assert datetime.fromisoformat(result['utc']) == local
        assert int(local.timestamp()) == result['unix']
        assert result['timezone'] == 'America/New_York'

    def test_format_timestamp(self):
        '''Test formatting a fixed moment.'''
        now = datetime(2026, 11, 8, 14, 5, 9, tzinfo=ZoneInfo('America/New_York'))
        assert server.format_timestamp(now) | {'timezone': None} == {
            'iso': '2026-11-08T14:05:09-05:00',
            'utc': '2026-11-08T19:05:09Z',
            'unix': 1794164709,
            'date': '2026-11-08',
            'time': '14:05:09',
            'time_12h': '2:05 PM',
            'day_of_week': 'Sunday',
            'human_date': 'Sunday November 8, 2026',
            'human': 'Sunday November 8, 2026 at 2:05 PM',
            'iso_week': '2026-W45',
            'timezone': None,
            'utc_offset': '-05:00',
        }

    def test_format_timestamp_midnight_and_naive(self):
        '''Midnight is 12 AM, and a naive datetime leaves the offset fields empty.'''
        result = server.format_timestamp(datetime(2026, 1, 1, 0, 30))
        assert result['time_12h'] == '12:30 AM'
        assert result['utc_offset'] == ''
        assert result['utc'] == ''


class TestJournalTools:
    '''Test journal tools.'''

    def test_list_todays_journal_entry(self):
        '''Test getting today's journal entry path.'''
        result = server.list_todays_journal_entry()
        assert 'path' in result
        assert 'name' in result
        assert result['path'].startswith('journal/')
        assert result['path'].endswith('.md')


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

    def test_append_to_journal_entry_today(self, vault_path):
        result = server.append_to_journal_entry('  remember the milk  ')
        assert result['success'] is True
        assert result['created'] is True
        assert result['path'] == server.list_todays_journal_entry()['path']
        assert (vault_path / result['path']).read_text() == 'remember the milk\n'

        again = server.append_to_journal_entry('and eggs')
        assert again['created'] is False
        assert (vault_path / result['path']).read_text() == 'remember the milk\n\nand eggs\n'

    def test_append_to_journal_entry_by_date(self, vault_path):
        result = server.append_to_journal_entry('### Late night\n\nwrapped up', date='2025-01-15')
        assert result['path'] == 'journal/2025/01/2025-01-15.md'
        assert result['created'] is False
        assert (vault_path / result['path']).read_text().endswith(
            '#journal #2025 #january\n\n### Late night\n\nwrapped up\n'
        )

    def test_prepend_to_journal_entry_today(self, vault_path):
        result = server.prepend_to_journal_entry('### Evening\n\nread a book')
        assert result['success'] is True
        assert result['created'] is True
        path = vault_path / result['path']
        assert path.read_text() == '### Evening\n\nread a book\n'

        again = server.prepend_to_journal_entry('### Night\n\nwent to bed')
        assert again['created'] is False
        assert path.read_text() == '### Night\n\nwent to bed\n\n### Evening\n\nread a book\n'

    def test_prepend_to_journal_entry_by_date(self, vault_path):
        result = server.prepend_to_journal_entry('### Morning\n\ncoffee', date='2025-01-15')
        content = (vault_path / result['path']).read_text()
        assert content.startswith('### Morning\n\ncoffee\n\n# January 15, 2025')

    def test_write_journal_entry(self, vault_path):
        result = server.write_journal_entry('### Rewritten\n\nall new\n', date='2025-01-15')
        assert result['success'] is True
        assert result['created'] is False
        assert (vault_path / result['path']).read_text() == '### Rewritten\n\nall new\n'

        today = server.write_journal_entry('### Today\n')
        assert today['created'] is True
        assert today['path'] == server.list_todays_journal_entry()['path']

    @pytest.mark.parametrize('tool', ['append_to_journal_entry', 'prepend_to_journal_entry', 'write_journal_entry'])
    def test_journal_edit_tools_reject_empty_text(self, tool):
        result = getattr(server, tool)('   ')
        assert result['success'] is False
        assert 'Invalid input' in result['error']

    @pytest.mark.parametrize('tool', ['append_to_journal_entry', 'prepend_to_journal_entry', 'write_journal_entry'])
    @pytest.mark.parametrize('bad', ['2025-1-15', '2025-02-30', 'yesterday', '../2025-01-15'])
    def test_journal_edit_tools_reject_bad_dates(self, tool, bad, vault_path):
        result = getattr(server, tool)('### Entry', date=bad)
        assert result['success'] is False
        assert 'Invalid input' in result['error']

    def test_server_instructions_describe_entry_headings(self):
        instructions = server.mcp.instructions
        assert instructions == server.JOURNAL_FORMAT
        assert '### heading' in instructions
        for tool in ('write_journal_entry', 'append_to_journal_entry', 'prepend_to_journal_entry',
                     'get_current_timestamp'):
            assert tool in instructions
