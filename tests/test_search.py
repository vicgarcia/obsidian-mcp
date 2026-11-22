'''
Tests for journal search: note splitting, matching, date ranges and the tool.
'''

import pytest
from pydantic import ValidationError

from obsidian_mcp import server
from obsidian_mcp.schema import JournalSearchInput, parse_search_terms
from obsidian_mcp.vault_client import VaultClient, split_journal_notes


RUN_DAY = '''# Recap

quiet sunday, mostly outside

### Morning run

first time on the river trail, much better
than the road loop

#### Notes

- 5.2 miles

2026-03-01 07:50


### Dentist

called about the insurance claim, they
need the dentist's form again

2026-03-01 11:15


'''

FENCED_DAY = '''### Shell notes

```bash
### not a heading inside a fence
echo hello
```

still the shell note

2026-03-02 09:00


'''


def write_entry(vault_path, date, content):
    year, month, _ = date.split('-')
    folder = vault_path / 'journal' / year / month
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f'{date}.md').write_text(content, encoding='utf-8', newline='')


@pytest.fixture
def journal(vault_path):
    write_entry(vault_path, '2026-03-01', RUN_DAY)
    write_entry(vault_path, '2026-03-02', FENCED_DAY)
    write_entry(vault_path, '2025-12-31', '### Year end\n\nanother river trail run to close the year\n\n2025-12-31 16:00\n')
    write_entry(vault_path, '2026-04-10', '### Garden\n\nplanted tomatoes\n\n2026-04-10 18:30\n')
    return vault_path


@pytest.fixture
def vault(journal):
    return VaultClient(str(journal))


@pytest.fixture
def tool_client(journal):
    server._client = VaultClient(str(journal))
    yield
    server._client = None


class TestSplitNotes:
    '''Entries are split on ### headings outside code fences.'''

    def test_splits_preamble_and_notes(self):
        notes = split_journal_notes(RUN_DAY)
        assert [n['heading'] for n in notes] == [None, 'Morning run', 'Dentist']
        assert notes[0]['body'] == '# Recap\n\nquiet sunday, mostly outside'
        assert notes[0]['timestamp'] is None

    def test_timestamp_is_pulled_off_the_body(self):
        run = split_journal_notes(RUN_DAY)[1]
        assert run['timestamp'] == '2026-03-01 07:50'
        assert run['body'].endswith('- 5.2 miles')
        assert '#### Notes' in run['body']

    def test_heading_inside_a_fence_is_not_a_note(self):
        notes = split_journal_notes(FENCED_DAY)
        assert len(notes) == 1
        assert notes[0]['heading'] == 'Shell notes'
        assert '### not a heading inside a fence' in notes[0]['body']
        assert notes[0]['body'].endswith('still the shell note')

    def test_blank_preamble_is_dropped(self):
        assert split_journal_notes('\n\n### Only\n\ntext\n')[0]['heading'] == 'Only'

    def test_file_without_notes_is_one_section(self):
        notes = split_journal_notes('just some text\n')
        assert notes == [{'heading': None, 'body': 'just some text', 'timestamp': None}]

    def test_crlf_files_split_the_same(self):
        notes = split_journal_notes(RUN_DAY.replace('\n', '\r\n'))
        assert [n['heading'] for n in notes] == [None, 'Morning run', 'Dentist']
        assert notes[1]['timestamp'] == '2026-03-01 07:50'


class TestSearchTerms:
    '''Queries split into words, with quoted phrases kept together.'''

    def test_words_are_lowercased(self):
        assert parse_search_terms('River  TRAIL') == ['river', 'trail']

    def test_quoted_phrase_is_one_term(self):
        assert parse_search_terms('"river   trail" run') == ['river trail', 'run']

    def test_empty_quotes_are_ignored(self):
        assert parse_search_terms('"" run') == ['run']


class TestSearchInput:
    '''Validation for the search tool's arguments.'''

    def test_defaults(self):
        validated = JournalSearchInput(query=' run ')
        assert validated.query == 'run'
        assert validated.max_results == 20
        assert validated.start_date is None and validated.end_date is None

    @pytest.mark.parametrize('query', ['', '   ', '""', 'x' * 201])
    def test_bad_queries(self, query):
        with pytest.raises(ValidationError):
            JournalSearchInput(query=query)

    @pytest.mark.parametrize('max_results', [0, 51, -1])
    def test_max_results_bounds(self, max_results):
        with pytest.raises(ValidationError):
            JournalSearchInput(query='run', max_results=max_results)

    def test_bad_dates(self):
        with pytest.raises(ValidationError):
            JournalSearchInput(query='run', start_date='2026-02-30')
        with pytest.raises(ValidationError):
            JournalSearchInput(query='run', end_date='March 1')

    def test_start_after_end(self):
        with pytest.raises(ValidationError):
            JournalSearchInput(query='run', start_date='2026-03-02', end_date='2026-03-01')


class TestVaultSearch:
    '''Searching the vault's journal.'''

    def test_all_words_must_be_in_the_same_note(self, vault):
        # insurance and run are both in 2026-03-01, but in different notes
        assert vault.search_journal(['insurance', 'run'])['total_matches'] == 0
        result = vault.search_journal(['insurance', 'dentist'])
        assert [r['heading'] for r in result['results']] == ['Dentist']

    def test_match_ignores_case_and_line_breaks(self, vault):
        result = vault.search_journal(['much better than the road'])
        assert [r['heading'] for r in result['results']] == ['Morning run']

    def test_heading_counts_as_note_text(self, vault):
        result = vault.search_journal(['garden'])
        assert result['results'][0]['date'] == '2026-04-10'

    def test_preamble_is_searchable(self, vault):
        result = vault.search_journal(['quiet sunday'])
        assert result['results'][0]['heading'] is None

    def test_newest_day_first_across_years(self, vault):
        result = vault.search_journal(['river trail'])
        assert [r['date'] for r in result['results']] == ['2026-03-01', '2025-12-31']

    def test_result_fields(self, vault):
        result = vault.search_journal(['tomatoes'])
        assert result['results'] == [{
            'date': '2026-04-10',
            'path': 'journal/2026/04/2026-04-10.md',
            'heading': 'Garden',
            'timestamp': '2026-04-10 18:30',
            'snippet': 'planted tomatoes',
        }]
        assert result['truncated'] is False
        assert result['entries_searched'] == 5

    def test_date_range_is_inclusive(self, vault):
        result = vault.search_journal(['river'], start_date='2026-01-01', end_date='2026-03-01')
        assert [r['date'] for r in result['results']] == ['2026-03-01']
        result = vault.search_journal(['river'], end_date='2025-12-31')
        assert [r['date'] for r in result['results']] == ['2025-12-31']

    def test_range_skips_entries_outside_it(self, vault):
        result = vault.search_journal(['anything'], start_date='2026-04-01')
        assert result['entries_searched'] == 1

    def test_truncation_reports_the_total(self, vault):
        result = vault.search_journal(['2026'], max_results=1)
        # matches nothing: timestamps are not part of the searched text
        assert result['total_matches'] == 0
        result = vault.search_journal(['the'], max_results=1)
        assert len(result['results']) == 1
        assert result['total_matches'] > 1
        assert result['truncated'] is True

    def test_fenced_text_is_searchable(self, vault):
        result = vault.search_journal(['echo hello'])
        assert [r['heading'] for r in result['results']] == ['Shell notes']

    def test_ignores_files_and_folders_that_are_not_entries(self, journal, vault):
        (journal / 'journal' / '2026' / '03' / 'ideas.md').write_text('river')
        (journal / 'journal' / 'templates').mkdir()
        (journal / 'journal' / 'templates' / 'river.md').write_text('river')
        (journal / 'journal' / '2026' / '13').mkdir()
        assert vault.search_journal(['river'])['total_matches'] == 2

    def test_skips_unreadable_entries(self, journal, vault):
        (journal / 'journal' / '2026' / '03' / '2026-03-03.md').write_bytes(b'\xff\xfe\x00river')
        assert vault.search_journal(['river'])['total_matches'] == 2

    def test_no_journal_folder(self, tmp_path):
        empty = tmp_path / 'empty'
        empty.mkdir()
        result = VaultClient(str(empty)).search_journal(['run'])
        assert result == {'results': [], 'total_matches': 0, 'truncated': False, 'entries_searched': 0}


class TestSnippet:
    '''Snippets are short and centered near the first match.'''

    def test_long_note_snippet_is_trimmed_around_the_match(self, journal, vault):
        filler = ' '.join(f'word{i}' for i in range(200))
        write_entry(journal, '2026-05-01', f'### Long\n\n{filler} needle {filler}\n')
        snippet = vault.search_journal(['needle'])['results'][0]['snippet']
        assert 'needle' in snippet
        assert snippet.startswith('…') and snippet.endswith('…')
        assert len(snippet) <= 202

    def test_heading_only_match_starts_at_the_body(self, vault):
        snippet = vault.search_journal(['dentist', 'claim'])['results'][0]['snippet']
        assert snippet.startswith('called about the insurance claim')


class TestSearchTool:
    '''The MCP tool wraps validation and the vault search.'''

    def test_returns_results(self, tool_client):
        result = server.search_journal('"river trail"', start_date='2026-01-01')
        assert result['query'] == '"river trail"'
        assert [r['date'] for r in result['results']] == ['2026-03-01']

    def test_invalid_input(self, tool_client):
        result = server.search_journal('run', max_results=500)
        assert result['success'] is False
        assert 'Invalid input' in result['error']

    def test_instructions_mention_search(self):
        assert 'search_journal' in server.mcp.instructions
