''' test configuration and fixtures for the Obsidian MCP server tests. '''

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
