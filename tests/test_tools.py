'''
Tests for MCP tools.
'''

import os
import stat
import sys

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
    def test_tz_decides_today_for_every_date_tool(self, monkeypatch, tz, vault_path):
        '''These zones are 25 hours apart, so at least one differs from the system date.'''
        monkeypatch.setenv('TZ', tz)
        expected = datetime.now(ZoneInfo(tz))

        result = server.get_todays_date()
        assert result['date'] == expected.strftime('%Y-%m-%d')
        assert result['timezone'] == tz
        note = server.add_note_to_journal_entry('### Topic\nbody')
        assert expected.strftime('%Y-%m-%d') in note['path']
        assert note['timestamp'].startswith(expected.strftime('%Y-%m-%d'))

    def test_get_todays_date(self, monkeypatch):
        '''Today's date has the date, time, weekday and timezone, and they agree.'''
        monkeypatch.setenv('TZ', 'America/New_York')
        result = server.get_todays_date()
        assert set(result) == {'date', 'time', 'day_of_week', 'timezone'}
        local = datetime.strptime(f"{result['date']} {result['time']}", '%Y-%m-%d %I:%M %p')
        assert local.strftime('%A') == result['day_of_week']
        assert result['timezone'] == 'America/New_York'

    @pytest.mark.parametrize('hour, minute, expected', [
        (0, 0, '12:00 AM'), (0, 30, '12:30 AM'), (9, 5, '9:05 AM'), (11, 59, '11:59 AM'),
        (12, 0, '12:00 PM'), (13, 7, '1:07 PM'), (23, 59, '11:59 PM'),
    ])
    def test_get_todays_date_12_hour_time(self, monkeypatch, hour, minute, expected):
        now = datetime(2026, 11, 14, hour, minute, tzinfo=ZoneInfo('America/New_York'))
        monkeypatch.setattr(VaultClient, 'get_local_datetime', lambda self: now)
        assert server.get_todays_date()['time'] == expected

    def test_get_todays_date_fixed_moment(self, monkeypatch):
        '''A fixed moment formats as 24-hour time with no seconds.'''
        now = datetime(2026, 11, 14, 9, 5, 59, tzinfo=ZoneInfo('America/New_York'))
        monkeypatch.setattr(VaultClient, 'get_local_datetime', lambda self: now)
        monkeypatch.setenv('TZ', 'America/New_York')
        assert server.get_todays_date() == {
            'date': '2026-11-14',
            'time': '9:05 AM',
            'day_of_week': 'Saturday',
            'timezone': 'America/New_York',
        }


class TestJournalTools:
    '''Test journal tools.'''

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
    '''Test reading journal entries by date and editing them.'''

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

    def test_append_to_journal_entry_is_exact(self, vault_path):
        result = server.append_to_journal_entry('  remember the milk  ')
        assert result['success'] is True
        assert result['created'] is True
        assert result['path'] == server.read_journal_entry(server.get_todays_date()['date'])['path']
        path = vault_path / result['path']
        assert path.read_bytes() == b'  remember the milk  '

        again = server.append_to_journal_entry('and eggs\n')
        assert again['created'] is False
        assert path.read_bytes() == b'  remember the milk  and eggs\n'

    def test_append_to_journal_entry_by_date(self, vault_path):
        result = server.append_to_journal_entry('\n### Late night\nwrapped up\n', date='2025-01-15')
        assert result['path'] == 'journal/2025/01/2025-01-15.md'
        assert result['created'] is False
        assert (vault_path / result['path']).read_text().endswith(
            '#journal #2025 #january\n\n### Late night\nwrapped up\n'
        )

    def test_prepend_to_journal_entry_is_exact(self, vault_path):
        result = server.prepend_to_journal_entry('# Recap\nread a book')
        assert result['success'] is True
        assert result['created'] is True
        path = vault_path / result['path']
        assert path.read_bytes() == b'# Recap\nread a book'

        again = server.prepend_to_journal_entry('# Mood\ngood\n\n')
        assert again['created'] is False
        assert path.read_bytes() == b'# Mood\ngood\n\n# Recap\nread a book'

    def test_prepend_to_journal_entry_by_date(self, vault_path):
        result = server.prepend_to_journal_entry('# Recap\ncoffee\n\n', date='2025-01-15')
        content = (vault_path / result['path']).read_text()
        assert content.startswith('# Recap\ncoffee\n\n# January 15, 2025')

    def test_write_journal_entry(self, vault_path):
        result = server.write_journal_entry('### Rewritten\n\nall new\n', date='2025-01-15')
        assert result['success'] is True
        assert result['created'] is False
        assert (vault_path / result['path']).read_bytes() == b'### Rewritten\n\nall new\n'

        today = server.write_journal_entry('### Today\n')
        assert today['created'] is True
        assert today['path'] == server.read_journal_entry(server.get_todays_date()['date'])['path']

    def test_add_note_to_journal_entry_today(self, vault_path, monkeypatch):
        now = datetime(2026, 11, 14, 9, 14)
        monkeypatch.setattr(VaultClient, 'get_local_datetime', lambda self: now)
        first = server.add_note_to_journal_entry('### Coffee\nfirst cup\n')
        assert first == {
            'success': True,
            'path': 'journal/2026/11/2026-11-14.md',
            'created': True,
            'timestamp': '2026-11-14 09:14',
        }
        now = datetime(2026, 11, 14, 15, 40)
        second = server.add_note_to_journal_entry('### Walk\n#### Route\nriver trail')
        assert second['created'] is False
        assert (vault_path / first['path']).read_bytes() == (
            b'\n\n# Daily Notes\n'
            b'### Coffee\nfirst cup\n2026-11-14 09:14\n\n'
            b'### Walk\n#### Route\nriver trail\n2026-11-14 15:40\n\n'
        )

    def test_add_note_after_midnight_to_the_prior_day(self, vault_path, monkeypatch):
        now = datetime(2026, 11, 15, 0, 45)
        monkeypatch.setattr(VaultClient, 'get_local_datetime', lambda self: now)
        result = server.add_note_to_journal_entry('### Late night\nstill up', date='2026-11-14')
        assert result['path'] == 'journal/2026/11/2026-11-14.md'
        assert result['timestamp'] == '2026-11-15 00:45'

    @pytest.mark.parametrize('bad', [
        '',
        '   ',
        'no heading',
        '#### Section first',
        '## Topic',
        '### Topic\n## Breaks out',
        '### Topic\n# Breaks out',
    ])
    def test_add_note_rejects_bad_notes(self, bad, vault_path):
        result = server.add_note_to_journal_entry(bad)
        assert result['success'] is False
        assert 'Invalid input' in result['error']
        assert list((vault_path / 'journal').rglob('*.md')) == [vault_path / 'journal/2025/01/2025-01-15.md']

    def test_add_note_allows_hash_lines_in_code_blocks(self, vault_path):
        result = server.add_note_to_journal_entry('### Setup\n```bash\n# install deps\nuv sync\n```')
        assert result['success'] is True

    @pytest.mark.parametrize('tool', ['append_to_journal_entry', 'prepend_to_journal_entry', 'write_journal_entry'])
    def test_journal_edit_tools_reject_empty_text(self, tool):
        result = getattr(server, tool)('')
        assert result['success'] is False
        assert 'Invalid input' in result['error']

    @pytest.mark.parametrize('tool', ['append_to_journal_entry', 'prepend_to_journal_entry'])
    def test_append_and_prepend_accept_whitespace_only_text(self, tool, vault_path):
        result = getattr(server, tool)('\n\n')
        assert result['success'] is True
        assert (vault_path / result['path']).read_bytes() == b'\n\n'

    @pytest.mark.parametrize('tool', ['append_to_journal_entry', 'prepend_to_journal_entry',
                                      'write_journal_entry', 'add_note_to_journal_entry'])
    @pytest.mark.parametrize('bad', ['2025-1-15', '2025-02-30', 'yesterday', '../2025-01-15'])
    def test_journal_edit_tools_reject_bad_dates(self, tool, bad, vault_path):
        result = getattr(server, tool)('### Entry', date=bad)
        assert result['success'] is False
        assert 'Invalid input' in result['error']

    def test_server_instructions_describe_daily_notes(self):
        instructions = server.mcp.instructions
        assert instructions == server.JOURNAL_FORMAT
        assert '# Daily Notes' in instructions
        assert '### heading' in instructions
        for tool in ('add_note_to_journal_entry', 'write_journal_entry', 'append_to_journal_entry',
                     'prepend_to_journal_entry', 'read_journal_entry', 'get_todays_date'):
            assert tool in instructions


class TestErrorsHideVaultPath:
    '''Error responses use vault-relative paths and never reveal where the vault lives.'''

    @pytest.fixture
    def locked_entry(self, vault_path):
        '''A read-only journal file, so every write to it fails with an OSError.'''
        entry = vault_path / 'journal/2025/01/2025-01-15.md'
        os.chmod(entry, stat.S_IREAD)
        yield entry
        os.chmod(entry, stat.S_IREAD | stat.S_IWRITE)

    def _assert_hidden(self, result, vault_path):
        assert result['success'] is False
        text = repr(result).lower()
        root = str(vault_path)
        for form in {root, root.replace('\\', '/'), root.replace('\\', '\\\\')}:
            assert form.lower() not in text

    @pytest.mark.parametrize('call', [
        lambda: server.append_to_journal_entry('x', date='2025-01-15'),
        lambda: server.prepend_to_journal_entry('x', date='2025-01-15'),
        lambda: server.add_note_to_journal_entry('### x\ny', date='2025-01-15'),
        lambda: server.write_journal_entry('x', date='2025-01-15'),
        lambda: server.write_file('journal/2025/01/2025-01-15.md', 'x'),
    ])
    def test_write_failures_name_only_the_relative_path(self, call, locked_entry, vault_path):
        result = call()
        self._assert_hidden(result, vault_path)
        assert 'journal/2025/01/2025-01-15.md' in result['error']

    def test_missing_vault_is_not_named(self, vault_path):
        server._client = VaultClient(str(vault_path / 'gone'))
        result = server.read_journal_entry('2025-01-15')
        self._assert_hidden(result, vault_path)
        assert result['error'] == 'Vault directory does not exist'

    def test_path_outside_the_vault_is_reported_as_given(self, vault_path):
        result = server.read_file('../outside.md')
        self._assert_hidden(result, vault_path)

    def test_redact_catches_every_form_of_the_vault_path(self, vault_path):
        root = str(vault_path)
        message = f"raw {root} repr {root.replace(chr(92), chr(92) * 2)} slashes {root.replace(chr(92), '/')} upper {root.upper()}"
        redacted = server.redact_vault_path(message)
        assert redacted == 'raw <vault> repr <vault> slashes <vault> upper <vault>'

    def test_unexpected_errors_are_redacted(self, vault_path, monkeypatch):
        def boom(self, year, month):
            raise RuntimeError(f'could not list {vault_path}/journal')
        monkeypatch.setattr(VaultClient, 'list_journal_entries', boom)
        result = server.list_journal_entries_by_year_and_month('2025', '01')[0]
        self._assert_hidden(result, vault_path)
        assert '<vault>/journal' in result['error']


class TestFileToolsStayInTheVault:
    '''read_file and write_file can't reach anything outside the vault, on any platform.'''

    @pytest.fixture
    def outside(self, vault_path):
        '''A secret file beside the vault, and a sibling folder whose name starts with the vault's.'''
        secret = vault_path.parent / 'outside' / 'secret.md'
        secret.parent.mkdir()
        secret.write_text('SECRET')
        sibling = vault_path.parent / f'{vault_path.name}-evil' / 'secret.md'
        sibling.parent.mkdir()
        sibling.write_text('SECRET')
        (vault_path / 'projects' / 'p').mkdir()
        yield secret
        assert secret.read_text() == 'SECRET'
        assert sibling.read_text() == 'SECRET'

    def _attempts(self, vault_path, secret):
        absolute = str(secret)
        return [
            '../outside/secret.md',
            'projects/../../outside/secret.md',
            '..\\outside\\secret.md',
            f'../{vault_path.name}-evil/secret.md',
            absolute,
            absolute.replace('\\', '/'),
            '/' + absolute.lstrip('/\\'),
            '\\\\localhost\\share\\secret.md',
            '\\\\?\\' + absolute,
            'C:outside\\secret.md',
            'projects/p/x.md:hidden',
            'projects/p/NUL.md',
        ]

    def test_escape_attempts_are_refused(self, vault_path, outside):
        for path in self._attempts(vault_path, outside):
            read = server.read_file(path)
            write = server.write_file(path, 'OVERWRITTEN')
            assert read['success'] is False, path
            assert write['success'] is False, path
            assert 'Invalid input' in read['error'] and 'Invalid input' in write['error'], path
        # nothing new was written inside the vault either
        assert list((vault_path / 'projects').rglob('*')) == [vault_path / 'projects' / 'p']

    def _link_or_skip(self, link, target):
        '''A directory link from inside the vault to outside it: a symlink, or a junction on windows.'''
        try:
            link.symlink_to(target, target_is_directory=True)
            return
        except OSError:
            pass
        if sys.platform == 'win32':
            import _winapi
            _winapi.CreateJunction(str(target), str(link))
            return
        pytest.skip('cannot create a directory link here')

    def test_links_out_of_the_vault_are_refused(self, vault_path, outside):
        link = vault_path / 'projects' / 'p' / 'link'
        self._link_or_skip(link, outside.parent)
        for path in ('projects/p/link/secret.md', 'projects/p/link/new.md'):
            read = server.read_file(path)
            write = server.write_file(path, 'OVERWRITTEN')
            assert 'outside vault' in read['error'] and 'outside vault' in write['error'], path
        assert not (outside.parent / 'new.md').exists()

    def test_file_symlink_out_of_the_vault_is_refused(self, vault_path, outside):
        link = vault_path / 'projects' / 'p' / 'link.md'
        try:
            link.symlink_to(outside)
        except OSError:
            pytest.skip('cannot create a file symlink here (windows without developer mode)')
        assert 'outside vault' in server.read_file('projects/p/link.md')['error']
        assert 'outside vault' in server.write_file('projects/p/link.md', 'OVERWRITTEN')['error']

    def test_backslash_paths_work_on_every_platform(self, vault_path):
        assert server.write_file('projects\\garage\\plan.md', 'shelves') == {'success': True}
        assert (vault_path / 'projects' / 'garage' / 'plan.md').read_text() == 'shelves'
        assert server.read_file('projects/garage/plan.md') == {'content': 'shelves'}
