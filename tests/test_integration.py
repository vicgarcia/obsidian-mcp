'''
Integration tests for complete workflows.
'''

import pytest
from pathlib import Path

from obsidian_mcp.vault_client import VaultClient
from obsidian_mcp import server


@pytest.fixture(autouse=True)
def setup_client(vault_path):
    '''Set up the vault client singleton for tools.'''
    server._client = VaultClient(str(vault_path))
    yield
    server._client = None


class TestJournalWorkflow:
    '''Integration tests for journal workflow.'''

    def test_full_journal_workflow(self, vault_path):
        '''Test a complete journal workflow.'''
        today_path = 'journal/2025/01/2025-01-20.md'
        content = '# January 20, 2025\n\n## Notes\nTest entry'

        result = server.write_file(today_path, content)
        assert result == {'success': True}

        result = server.read_file(today_path)
        assert 'content' in result
        assert 'January 20, 2025' in result['content']

        result = server.list_journal_entries_by_year_and_month('2025', '01')
        assert isinstance(result, list)
        entry_names = [e['name'] for e in result if 'name' in e]
        assert '2025-01-20.md' in entry_names


class TestProjectWorkflow:
    '''Integration tests for project workflow.'''

    def test_full_project_workflow(self, vault_path):
        '''Test a complete project workflow.'''
        result = server.create_project('integration-test-project')
        assert result == {'success': True}

        content = '# Project Overview\n\nProject details here.'
        result = server.write_file('projects/integration-test-project/overview.md', content)
        assert result == {'success': True}

        result = server.read_file('projects/integration-test-project/overview.md')
        assert 'Project Overview' in result['content']

        result = server.list_projects()
        project_names = [p['name'] for p in result if 'name' in p]
        assert 'integration-test-project' in project_names

        result = server.list_project_content('integration-test-project')
        file_names = [f['name'] for f in result if 'name' in f]
        assert 'overview.md' in file_names


class TestWikiWorkflow:
    '''Integration tests for wiki workflow.'''

    def test_full_wiki_workflow(self, vault_path):
        '''Test a complete wiki workflow.'''
        wiki_dir = vault_path / 'wiki'
        wiki_dir.mkdir(parents=True, exist_ok=True)

        content = '# Kubernetes Guide\n\nComplete K8s reference.'
        result = server.write_file('wiki/kubernetes.md', content)
        assert result == {'success': True}

        result = server.read_file('wiki/kubernetes.md')
        assert 'Kubernetes Guide' in result['content']

        result = server.list_wiki()
        article_names = [a['name'] for a in result if 'name' in a]
        assert 'kubernetes.md' in article_names


class TestVaultClientWorkflow:
    '''Integration tests using VaultClient directly.'''

    def test_complete_vault_operations(self, vault_path):
        '''Test complete vault operations through VaultClient.'''
        with VaultClient(str(vault_path)) as vault:
            vault.write_file('integration/test.md', '# Integration Test')
            content = vault.read_file('integration/test.md')
            assert '# Integration Test' in content

            assert vault.file_exists('integration/test.md') is True
            assert vault.file_exists('integration/nonexistent.md') is False

            vault.create_directory('integration/subdir')
            assert vault.directory_exists('integration/subdir') is True

            files = vault.list_files('integration', recursive=True)
            assert len(files) >= 1
            assert any(f['name'] == 'test.md' for f in files)
