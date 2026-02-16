import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# set the test vault path
TEST_VAULT_PATH = Path(__file__).parent / "fixtures" / "vault"


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    ''' set up the test environment with the test vault path. '''
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(TEST_VAULT_PATH.absolute()))


@pytest.fixture
def vault_path():
    ''' return the test vault path. '''
    return TEST_VAULT_PATH


@pytest.fixture
def mock_mcp_server():
    ''' create a mock MCP server for testing tool registration. '''
    mock_server = MagicMock()
    mock_server.tool = lambda: lambda func: func  # simple decorator that returns the function
    return mock_server


@pytest.fixture
def sample_journal_entries():
    ''' create sample journal entries for testing. '''
    return [
        {"path": "journal/2025/01/2025-01-15.md", "name": "2025-01-15.md"},
        {"path": "journal/2025/01/2025-01-16.md", "name": "2025-01-16.md"},
    ]


@pytest.fixture
def sample_file_content():
    ''' sample markdown file content for testing. '''
    return """# Test Note

This is a test note for the Obsidian MCP server.

## Content

Some content here with [[links]] and #tags.
"""


@pytest.fixture
def setup_wiki(vault_path):
    ''' create sample wiki articles for testing. '''
    wiki_dir = vault_path / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)

    # clean any existing files first
    for existing_file in wiki_dir.glob("*"):
        if existing_file.is_file():
            existing_file.unlink()

    # create test articles
    articles = {
        "python-asyncio.md": "# Python Asyncio\n\nComplete guide to async programming.",
        "docker-networking.md": "# Docker Networking\n\nNetworking concepts in Docker.",
        "git-workflows.md": "# Git Workflows\n\nBranching strategies and workflows.",
    }

    for filename, content in articles.items():
        (wiki_dir / filename).write_text(content)

    yield wiki_dir

    # cleanup all files
    for existing_file in wiki_dir.glob("*"):
        if existing_file.is_file():
            existing_file.unlink()


@pytest.fixture
def setup_prompts(vault_path):
    ''' create sample agent prompts for testing. '''
    prompts_dir = vault_path / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    # clean any existing files first
    for existing_file in prompts_dir.glob("*"):
        if existing_file.is_file():
            existing_file.unlink()

    # create test prompts
    prompts = {
        "code review assistant.md": "# Code Review Assistant\n\nYou are an assistant that will review code.",
        "documentation writer.md": "# Documentation Writer\n\nYou are an assistant that writes documentation.",
        "test generator.md": "# Test Generator\n\nYou are an assistant that generates tests.",
    }

    for filename, content in prompts.items():
        (prompts_dir / filename).write_text(content)

    yield prompts_dir

    # cleanup all files
    for existing_file in prompts_dir.glob("*"):
        if existing_file.is_file():
            existing_file.unlink()
