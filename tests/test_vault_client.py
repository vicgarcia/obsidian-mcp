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
            with pytest.raises(VaultError, match='Invalid path.*traversal'):
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


class TestJournalReadAndAppend:
    '''Test reading journal entries by date and appending to them.'''

    def test_read_existing_entry(self, vault_path):
        with VaultClient(str(vault_path)) as vault:
            result = vault.read_journal_entry(datetime(2025, 1, 15))
            assert result['path'] == 'journal/2025/01/2025-01-15.md'
            assert result['exists'] is True
            assert 'January 15, 2025' in result['content']

    def test_read_missing_entry(self, vault_path):
        with VaultClient(str(vault_path)) as vault:
            result = vault.read_journal_entry(datetime(2025, 1, 16))
            assert result == {'path': 'journal/2025/01/2025-01-16.md', 'exists': False, 'content': ''}

    def test_append_creates_entry_with_exact_text(self, vault_path):
        with VaultClient(str(vault_path)) as vault:
            result = vault.append_to_journal('first note', datetime(2025, 2, 3))
            assert result == {'path': 'journal/2025/02/2025-02-03.md', 'created': True}
        assert (vault_path / 'journal/2025/02/2025-02-03.md').read_bytes() == b'first note'

    def test_append_keeps_existing_content_and_adds_nothing(self, vault_path):
        entry = vault_path / 'journal/2025/01/2025-01-15.md'
        before = entry.read_bytes()
        with VaultClient(str(vault_path)) as vault:
            result = vault.append_to_journal('saw a heron', datetime(2025, 1, 15))
            assert result['created'] is False
        assert entry.read_bytes() == before + b'saw a heron'

    def test_append_twice_concatenates(self, vault_path):
        with VaultClient(str(vault_path)) as vault:
            vault.append_to_journal('one\n', datetime(2025, 3, 1))
            vault.append_to_journal('two', datetime(2025, 3, 1))
        assert (vault_path / 'journal/2025/03/2025-03-01.md').read_bytes() == b'one\ntwo'

    def test_append_writes_line_endings_as_given(self, vault_path):
        entry = vault_path / 'journal/2025/05/2025-05-01.md'
        entry.parent.mkdir(parents=True)
        entry.write_bytes(b'line one\r\n')
        with VaultClient(str(vault_path)) as vault:
            vault.append_to_journal('a\nb\n', datetime(2025, 5, 1))
        assert entry.read_bytes() == b'line one\r\na\nb\n'

    def test_append_defaults_to_today(self, vault_path):
        with VaultClient(str(vault_path)) as vault:
            result = vault.append_to_journal('today note')
            assert result['path'] == vault.get_journal_path()
        assert (vault_path / result['path']).exists()


class TestJournalPrependAndWrite:
    '''Test prepending to journal entries and replacing them.'''

    def _entry(self, vault_path, content: bytes):
        entry = vault_path / 'journal/2025/06/2025-06-01.md'
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_bytes(content)
        return entry

    def test_prepend_creates_entry_with_exact_text(self, vault_path):
        with VaultClient(str(vault_path)) as vault:
            result = vault.prepend_to_journal('### First', datetime(2025, 2, 3))
            assert result == {'path': 'journal/2025/02/2025-02-03.md', 'created': True}
        assert (vault_path / 'journal/2025/02/2025-02-03.md').read_bytes() == b'### First'

    def test_prepend_keeps_existing_content_and_adds_nothing(self, vault_path):
        entry = self._entry(vault_path, b'### Old\n\nold text\n')
        with VaultClient(str(vault_path)) as vault:
            result = vault.prepend_to_journal('### New\nnew text', datetime(2025, 6, 1))
            assert result['created'] is False
        assert entry.read_bytes() == b'### New\nnew text### Old\n\nold text\n'

    def test_prepend_keeps_leading_blank_lines(self, vault_path):
        entry = self._entry(vault_path, b'\n\n# Daily Notes\n')
        with VaultClient(str(vault_path)) as vault:
            vault.prepend_to_journal('# Recap\ngood day\n', datetime(2025, 6, 1))
        assert entry.read_bytes() == b'# Recap\ngood day\n\n\n# Daily Notes\n'

    def test_prepend_goes_right_after_frontmatter(self, vault_path):
        entry = self._entry(vault_path, b'---\ntags: [journal]\n---\n### Old\n')
        with VaultClient(str(vault_path)) as vault:
            vault.prepend_to_journal('### New\n', datetime(2025, 6, 1))
        assert entry.read_bytes() == b'---\ntags: [journal]\n---\n### New\n### Old\n'

    def test_prepend_after_frontmatter_only_file(self, vault_path):
        entry = self._entry(vault_path, b'---\nmood: good\n---')
        with VaultClient(str(vault_path)) as vault:
            vault.prepend_to_journal('### New', datetime(2025, 6, 1))
        assert entry.read_bytes() == b'---\nmood: good\n---\n### New'

    def test_prepend_treats_unclosed_rule_as_content(self, vault_path):
        entry = self._entry(vault_path, b'---\n### Old\n')
        with VaultClient(str(vault_path)) as vault:
            vault.prepend_to_journal('### New\n', datetime(2025, 6, 1))
        assert entry.read_bytes() == b'### New\n---\n### Old\n'

    def test_prepend_keeps_crlf_frontmatter_and_writes_text_as_given(self, vault_path):
        entry = self._entry(vault_path, b'---\r\na: 1\r\n---\r\n### Old\r\n')
        with VaultClient(str(vault_path)) as vault:
            vault.prepend_to_journal('### New\nline\n', datetime(2025, 6, 1))
        assert entry.read_bytes() == b'---\r\na: 1\r\n---\r\n### New\nline\n### Old\r\n'

    def test_prepend_defaults_to_today(self, vault_path):
        with VaultClient(str(vault_path)) as vault:
            result = vault.prepend_to_journal('### Today')
            assert result['path'] == vault.get_journal_path()

    def test_write_journal_entry_replaces_content(self, vault_path):
        entry = self._entry(vault_path, b'### Old\n')
        with VaultClient(str(vault_path)) as vault:
            result = vault.write_journal_entry('### Replaced\n', datetime(2025, 6, 1))
            assert result == {'path': 'journal/2025/06/2025-06-01.md', 'created': False}
        assert entry.read_bytes() == b'### Replaced\n'

    def test_write_journal_entry_creates(self, vault_path):
        with VaultClient(str(vault_path)) as vault:
            result = vault.write_journal_entry('### New\n', datetime(2025, 7, 4))
            assert result['created'] is True
        assert (vault_path / 'journal/2025/07/2025-07-04.md').exists()

    def test_write_file_keeps_lf_line_endings(self, vault_path):
        '''Windows text mode would write crlf; the vault stays lf.'''
        with VaultClient(str(vault_path)) as vault:
            vault.write_file('projects/notes.md', 'a\nb\n')
        assert (vault_path / 'projects/notes.md').read_bytes() == b'a\nb\n'


class TestJournalNotes:
    '''Test adding notes to the end of a journal entry.'''

    DAY = datetime(2026, 11, 14)

    @pytest.fixture
    def clock(self, monkeypatch):
        '''Pin the local time; set clock.now to move it.'''
        class Clock:
            now = datetime(2026, 11, 14, 9, 14)
        monkeypatch.setattr(VaultClient, 'get_local_datetime', lambda self: Clock.now)
        return Clock

    def _entry(self, vault_path, content: bytes | None = None):
        entry = vault_path / 'journal/2026/11/2026-11-14.md'
        if content is not None:
            entry.parent.mkdir(parents=True, exist_ok=True)
            entry.write_bytes(content)
        return entry

    def test_note_starts_a_new_file(self, vault_path, clock):
        with VaultClient(str(vault_path)) as vault:
            result = vault.add_note_to_journal('### Coffee\nfirst cup', self.DAY)
        assert result == {'path': 'journal/2026/11/2026-11-14.md', 'created': True, 'timestamp': '2026-11-14 09:14'}
        assert self._entry(vault_path).read_bytes() == b'### Coffee\nfirst cup\n\n2026-11-14 09:14\n\n\n'

    def test_no_section_heading_is_added(self, vault_path, clock):
        entry = self._entry(vault_path, b'# daily recap\n\ngood day\n')
        with VaultClient(str(vault_path)) as vault:
            vault.add_note_to_journal('### Note\nx', self.DAY)
        assert b'daily notes' not in entry.read_bytes().lower()

    def test_the_requested_layout(self, vault_path, clock):
        '''A note sent in the documented format reads with a blank line around every heading.'''
        with VaultClient(str(vault_path)) as vault:
            vault.add_note_to_journal(
                '### note heading\n\ncontent in the note\n\n#### note subheading\n\nmore content under subheading',
                self.DAY,
            )
        assert self._entry(vault_path).read_text() == (
            '### note heading\n'
            '\n'
            'content in the note\n'
            '\n'
            '#### note subheading\n'
            '\n'
            'more content under subheading\n'
            '\n'
            '2026-11-14 09:14\n'
            '\n'
            '\n'
        )

    def test_notes_through_the_day(self, vault_path, clock):
        with VaultClient(str(vault_path)) as vault:
            vault.add_note_to_journal('### One\nfirst', self.DAY)
            clock.now = datetime(2026, 11, 14, 23, 59)
            vault.add_note_to_journal('### Two\nsecond', self.DAY)
        assert self._entry(vault_path).read_bytes() == (
            b'### One\nfirst\n\n2026-11-14 09:14\n\n\n### Two\nsecond\n\n2026-11-14 23:59\n\n\n'
        )

    @pytest.mark.parametrize('content', [b'', b'\n', b'  \n\n'])
    def test_empty_file_starts_with_the_note(self, vault_path, clock, content):
        entry = self._entry(vault_path, content)
        with VaultClient(str(vault_path)) as vault:
            result = vault.add_note_to_journal('### Note\nx', self.DAY)
            assert result['created'] is False
        assert entry.read_bytes() == b'### Note\nx\n\n2026-11-14 09:14\n\n\n'

    @pytest.mark.parametrize('content, lead', [
        (b'# daily recap\ngood day', b'\n\n\n'),
        (b'# daily recap\ngood day\n', b'\n\n'),
        (b'# daily recap\ngood day\n\n', b'\n'),
        (b'# daily recap\ngood day\n\n\n', b''),
        (b'# daily recap\ngood day\n\n\n\n', b''),
    ])
    def test_existing_content_ends_in_two_blank_lines_before_the_note(self, vault_path, clock, content, lead):
        entry = self._entry(vault_path, content)
        with VaultClient(str(vault_path)) as vault:
            vault.add_note_to_journal('### Note\nx', self.DAY)
        assert entry.read_bytes() == content + lead + b'### Note\nx\n\n2026-11-14 09:14\n\n\n'

    def test_recap_prepended_above_existing_notes(self, vault_path, clock):
        with VaultClient(str(vault_path)) as vault:
            vault.add_note_to_journal('### Note\nx', self.DAY)
            vault.prepend_to_journal('# daily recap\n\nall good\n\n\n', self.DAY)
            vault.add_note_to_journal('### Later\ny', self.DAY)
        assert self._entry(vault_path).read_bytes() == (
            b'# daily recap\n\nall good\n\n\n'
            b'### Note\nx\n\n2026-11-14 09:14\n\n\n### Later\ny\n\n2026-11-14 09:14\n\n\n'
        )

    def test_note_defaults_to_today(self, vault_path, clock):
        with VaultClient(str(vault_path)) as vault:
            result = vault.add_note_to_journal('### Note\nx')
            assert result['path'] == 'journal/2026/11/2026-11-14.md'

    @pytest.mark.parametrize('note', [
        '### tight\nno blank line after the heading\n#### section\nor here',
        '### loose\n\n\n\nlots of blank lines\n\n\n#### section\n\n\nkept as sent',
        '### code\n\n```bash\n# a comment\n\n\nuv sync\n```',
        '# my own heading\n\n## and another\n\nheadings are up to the agent',
        'no heading at all',
    ])
    def test_note_content_is_written_exactly_as_sent(self, vault_path, clock, note):
        '''The tool never respaces or checks a note; only its ends are trimmed before the timestamp.'''
        with VaultClient(str(vault_path)) as vault:
            vault.add_note_to_journal(note, self.DAY)
        assert self._entry(vault_path).read_text() == f'{note}\n\n2026-11-14 09:14\n\n\n'
