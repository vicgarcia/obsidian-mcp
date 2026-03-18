'''
Pytest configuration and fixtures for Obsidian MCP tests.
'''

import pytest


SEED_JOURNAL_CONTENT = '''# January 15, 2025 - Wednesday

## Daily Notes

### Goals for Today
- Complete the Obsidian MCP server implementation
- Test all functionality

### Accomplishments
- Successfully built the MCP server
- Implemented all required tools

### Reflections
- The FastMCP framework makes it easy to build MCP servers
- Proper input validation is crucial for security

---

## Tags
#journal #2025 #january
'''


@pytest.fixture
def vault_path(tmp_path):
    '''
    Create a temporary vault for testing.

    Uses tmp_path (pytest built-in) so each test gets a fresh vault
    and all test artifacts are automatically cleaned up.
    '''
    vault = tmp_path / 'vault'
    vault.mkdir()

    # create standard directories
    (vault / 'journal').mkdir()
    (vault / 'projects').mkdir()
    (vault / 'wiki').mkdir()

    # create seed journal entry
    journal_dir = vault / 'journal' / '2025' / '01'
    journal_dir.mkdir(parents=True)
    (journal_dir / '2025-01-15.md').write_text(SEED_JOURNAL_CONTENT)

    return vault


@pytest.fixture
def setup_wiki(vault_path):
    '''Create sample wiki articles for testing.'''
    wiki_dir = vault_path / 'wiki'

    articles = {
        'python-asyncio.md': '# Python Asyncio\n\nComplete guide to async programming.',
        'docker-networking.md': '# Docker Networking\n\nNetworking concepts in Docker.',
        'git-workflows.md': '# Git Workflows\n\nBranching strategies and workflows.',
    }

    for filename, content in articles.items():
        (wiki_dir / filename).write_text(content)

    return wiki_dir
