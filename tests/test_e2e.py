''' end-to-end tests for the Obsidian MCP server. '''

import pytest
from pathlib import Path

from obsidian_mcp.server import read_file, write_file


class TestFileOperations:
    ''' test core file operations. '''

    def test_read_existing_file(self, vault_path):
        ''' test reading an existing file. '''
        result = read_file("journal/2025/01/2025-01-15.md")

        assert "content" in result
        assert "January 15, 2025" in result["content"]
        assert "#journal" in result["content"]

    def test_read_nonexistent_file(self):
        ''' test reading a non-existent file. '''
        result = read_file("nonexistent/file.md")

        assert "error" in result
        assert "File not found" in result["error"]

    def test_read_file_path_traversal(self):
        ''' test that path traversal is prevented in read operations. '''
        result = read_file("../../../etc/passwd")

        assert "error" in result
        assert "Invalid input" in result["error"]

    def test_write_new_file(self, vault_path):
        ''' test writing a new file. '''
        test_content = "# Test Note\n\nThis is test content."
        result = write_file("test/new_file.md", test_content)

        assert result == {"success": True}

        # verify file was created
        test_file = vault_path / "test" / "new_file.md"
        assert test_file.exists()
        assert test_file.read_text() == test_content

    def test_write_file_creates_directories(self, vault_path):
        ''' test that write_file creates parent directories. '''
        test_content = "# Deep Test\n\nNested content."
        result = write_file("deep/nested/path/test.md", test_content)

        assert result == {"success": True}

        # verify directory structure was created
        test_file = vault_path / "deep" / "nested" / "path" / "test.md"
        assert test_file.exists()
        assert test_file.parent.exists()

    def test_write_file_path_traversal(self):
        ''' test that path traversal is prevented in write operations. '''
        result = write_file("../../../tmp/evil.txt", "evil content")

        assert "error" in result
        assert "Invalid input" in result["error"]


class TestJournalTools:
    ''' test journal-related tools. '''

    def test_list_todays_journal_entry(self):
        ''' test getting today's journal entry path. '''
        # test the utility function that would be called by the tool
        from obsidian_mcp.utils import get_today_journal_path

        result_path = get_today_journal_path()
        assert result_path.startswith("journal/")
        assert result_path.endswith(".md")

    def test_list_journal_entries_by_year_and_month(self, vault_path):
        ''' test listing journal entries for a specific month. '''
        # create additional test entries
        test_dir = vault_path / "journal" / "2025" / "01"
        test_dir.mkdir(parents=True, exist_ok=True)

        (test_dir / "2025-01-16.md").write_text("# Jan 16\nContent")
        (test_dir / "2025-01-17.md").write_text("# Jan 17\nContent")

        # test the utility function that would be called by the tool
        from obsidian_mcp.utils import list_files_in_directory
        files = list_files_in_directory(test_dir, vault_path)

        # should find multiple journal entries
        assert len(files) >= 2
        assert any(f["name"] == "2025-01-15.md" for f in files)


class TestIntegration:
    ''' integration tests combining multiple operations. '''

    def test_full_workflow_journal(self, vault_path):
        ''' test a complete journal workflow. '''
        # 1. create a new journal entry
        today_path = f"journal/2025/01/2025-01-20.md"
        content = "# January 20, 2025\n\n## Notes\nTest entry"

        result = write_file(today_path, content)
        assert result == {"success": True}

        # 2. read it back
        result = read_file(today_path)
        assert "content" in result
        assert "January 20, 2025" in result["content"]

        # 3. verify it appears in directory listing
        from obsidian_mcp.utils import list_files_in_directory
        jan_dir = vault_path / "journal" / "2025" / "01"
        files = list_files_in_directory(jan_dir, vault_path)

        assert any(f["name"] == "2025-01-20.md" for f in files)
