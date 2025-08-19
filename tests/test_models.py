"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from obsidian_mcp.models import (
    JournalDateInput,
    YearMonthInput,
    FilePathInput,
    FileWriteInput,
    TopicInput,
    ProjectInput
)


class TestJournalDateInput:
    """Test journal date validation."""
    
    def test_valid_date(self):
        """Test valid date format."""
        valid_input = JournalDateInput(date="2025-01-15")
        assert valid_input.date == "2025-01-15"
    
    def test_invalid_format(self):
        """Test invalid date format."""
        with pytest.raises(ValidationError, match="YYYY-MM-DD format"):
            JournalDateInput(date="2025/01/15")
    
    def test_invalid_date(self):
        """Test invalid date."""
        with pytest.raises(ValidationError, match="Invalid date"):
            JournalDateInput(date="2025-02-30")


class TestYearMonthInput:
    """Test year/month validation."""
    
    def test_valid_year_month(self):
        """Test valid year and month."""
        valid_input = YearMonthInput(year="2025", month="01")
        assert valid_input.year == "2025"
        assert valid_input.month == "01"
    
    def test_invalid_year(self):
        """Test invalid year format."""
        with pytest.raises(ValidationError, match="YYYY format"):
            YearMonthInput(year="25", month="01")
    
    def test_invalid_month(self):
        """Test invalid month."""
        with pytest.raises(ValidationError, match="Month must be between 01 and 12"):
            YearMonthInput(year="2025", month="13")


class TestFilePathInput:
    """Test file path validation."""
    
    def test_valid_path(self):
        """Test valid file path."""
        valid_input = FilePathInput(file_path="journal/2025/01/test.md")
        assert valid_input.file_path == "journal/2025/01/test.md"
    
    def test_empty_path(self):
        """Test empty file path."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            FilePathInput(file_path="")
    
    def test_directory_traversal(self):
        """Test directory traversal prevention."""
        with pytest.raises(ValidationError, match="directory traversal"):
            FilePathInput(file_path="../../../etc/passwd")


class TestTopicInput:
    """Test topic name validation."""
    
    def test_valid_topic(self):
        """Test valid topic name."""
        valid_input = TopicInput(topic="machine-learning")
        assert valid_input.topic == "machine-learning"
    
    def test_empty_topic(self):
        """Test empty topic name."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            TopicInput(topic="")
    
    def test_invalid_characters(self):
        """Test invalid characters in topic name."""
        with pytest.raises(ValidationError, match="cannot contain"):
            TopicInput(topic="topic/with/slashes")


class TestProjectInput:
    """Test project name validation."""
    
    def test_valid_project(self):
        """Test valid project name."""
        valid_input = ProjectInput(project="website-redesign")
        assert valid_input.project == "website-redesign"
    
    def test_empty_project(self):
        """Test empty project name."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            ProjectInput(project="")
    
    def test_invalid_characters(self):
        """Test invalid characters in project name."""
        with pytest.raises(ValidationError, match="cannot contain"):
            ProjectInput(project="project*with*stars")