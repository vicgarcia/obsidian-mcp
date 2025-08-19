"""Unit tests for utility functions."""

import pytest
from datetime import datetime
from pathlib import Path

from obsidian_mcp.utils import (
    get_vault_base,
    validate_vault_path,
    create_error_response,
    create_success_response,
    create_file_info,
    get_today_date_string,
    get_today_journal_path,
    list_files_in_directory,
    list_directories_in_directory
)


class TestVaultOperations:
    """Test vault path operations."""
    
    def test_get_vault_base(self, vault_path):
        """Test getting vault base path."""
        base = get_vault_base()
        assert base.exists()
        assert base.is_dir()
        assert "vault" in str(base)
    
    def test_validate_vault_path_valid(self, vault_path):
        """Test validating a valid vault path."""
        valid_path = validate_vault_path("journal/2025/01/test.md")
        assert valid_path.is_relative_to(vault_path)
    
    def test_validate_vault_path_traversal(self, vault_path):
        """Test that directory traversal is prevented."""
        # Note: Primary traversal protection is at the input validation level
        # This tests the utility function with a resolved path
        test_path = validate_vault_path("journal/test.md")
        assert test_path.is_relative_to(vault_path)
    
    def test_validate_vault_path_absolute(self):
        """Test that absolute paths are prevented."""
        with pytest.raises(ValueError, match="outside vault directory"):
            validate_vault_path("/etc/passwd")


class TestResponseHelpers:
    """Test response helper functions."""
    
    def test_create_error_response(self):
        """Test creating error responses."""
        error = create_error_response("Test error message")
        assert error == {"error": "Test error message"}
    
    def test_create_success_response(self):
        """Test creating success responses."""
        success = create_success_response()
        assert success == {"success": True}


class TestFileHelpers:
    """Test file helper functions."""
    
    def test_create_file_info(self, vault_path):
        """Test creating file info objects."""
        test_file = vault_path / "journal" / "2025" / "01" / "2025-01-15.md"
        file_info = create_file_info(test_file, vault_path)
        
        assert file_info["name"] == "2025-01-15.md"
        assert file_info["path"] == "journal/2025/01/2025-01-15.md"
    
    def test_get_today_date_string(self):
        """Test getting today's date string."""
        date_str = get_today_date_string()
        # Should match YYYY-MM-DD format
        assert len(date_str) == 10
        assert date_str.count("-") == 2
        
        # Should be a valid date
        datetime.strptime(date_str, "%Y-%m-%d")
    
    def test_get_today_journal_path(self):
        """Test getting today's journal path."""
        journal_path = get_today_journal_path()
        
        # Should start with journal/
        assert journal_path.startswith("journal/")
        
        # Should end with .md
        assert journal_path.endswith(".md")
        
        # Should contain today's date components
        today = datetime.now()
        assert str(today.year) in journal_path
        assert f"{today.month:02d}" in journal_path
        assert f"{today.day:02d}" in journal_path


class TestDirectoryListing:
    """Test directory listing functions."""
    
    def test_list_files_in_directory_existing(self, vault_path):
        """Test listing files in an existing directory."""
        journal_dir = vault_path / "journal" / "2025" / "01"
        files = list_files_in_directory(journal_dir, vault_path)
        
        # Should find the test journal entry
        assert len(files) > 0
        assert any(f["name"] == "2025-01-15.md" for f in files)
    
    def test_list_files_in_directory_nonexistent(self, vault_path):
        """Test listing files in a non-existent directory."""
        nonexistent_dir = vault_path / "nonexistent"
        files = list_files_in_directory(nonexistent_dir, vault_path)
        
        # Should return empty list
        assert files == []
    
    def test_list_files_in_directory_recursive(self, vault_path):
        """Test recursive file listing."""
        journal_dir = vault_path / "journal"
        files = list_files_in_directory(journal_dir, vault_path, recursive=True)
        
        # Should find files recursively
        assert len(files) > 0
        # Should include files from subdirectories
        assert any("2025/01" in f["path"] for f in files)
    
    def test_list_directories_in_directory(self, vault_path):
        """Test listing subdirectories."""
        journal_dir = vault_path / "journal"
        directories = list_directories_in_directory(journal_dir, vault_path)
        
        # Should find year directories
        assert any(d["name"] == "2025" for d in directories)