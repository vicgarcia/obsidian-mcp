import pytest
from pydantic import ValidationError

from obsidian_mcp.models import (
    JournalDateInput,
    YearMonthInput,
    FilePathInput,
    FileWriteInput,
    ProjectInput
)


class TestJournalDateInput:
    ''' test journal date validation. '''

    def test_valid_date(self):
        ''' test valid date format. '''
        valid_input = JournalDateInput(date="2025-01-15")
        assert valid_input.date == "2025-01-15"

    def test_invalid_format(self):
        ''' test invalid date format. '''
        with pytest.raises(ValidationError, match="YYYY-MM-DD format"):
            JournalDateInput(date="2025/01/15")

    def test_invalid_date(self):
        ''' test invalid date. '''
        with pytest.raises(ValidationError, match="Invalid date"):
            JournalDateInput(date="2025-02-30")


class TestYearMonthInput:
    ''' test year/month validation. '''

    def test_valid_year_month(self):
        ''' test valid year and month. '''
        valid_input = YearMonthInput(year="2025", month="01")
        assert valid_input.year == "2025"
        assert valid_input.month == "01"

    def test_invalid_year(self):
        ''' test invalid year format. '''
        with pytest.raises(ValidationError, match="YYYY format"):
            YearMonthInput(year="25", month="01")

    def test_invalid_month(self):
        ''' test invalid month. '''
        with pytest.raises(ValidationError, match="Month must be between 01 and 12"):
            YearMonthInput(year="2025", month="13")


class TestFilePathInput:
    ''' test file path validation. '''

    def test_valid_path(self):
        ''' test valid file path. '''
        valid_input = FilePathInput(file_path="journal/2025/01/test.md")
        assert valid_input.file_path == "journal/2025/01/test.md"

    def test_empty_path(self):
        ''' test empty file path. '''
        with pytest.raises(ValidationError, match="cannot be empty"):
            FilePathInput(file_path="")

    def test_directory_traversal(self):
        ''' test directory traversal prevention. '''
        with pytest.raises(ValidationError, match="directory traversal"):
            FilePathInput(file_path="../../../etc/passwd")


class TestProjectInput:
    ''' test project name validation. '''

    def test_valid_project(self):
        ''' test valid project name. '''
        valid_input = ProjectInput(project="my-project")
        assert valid_input.project == "my-project"

    def test_empty_project(self):
        ''' test empty project name. '''
        with pytest.raises(ValidationError, match="cannot be empty"):
            ProjectInput(project="")

    def test_directory_traversal(self):
        ''' test directory traversal prevention. '''
        with pytest.raises(ValidationError, match="cannot contain"):
            ProjectInput(project="../etc")

    def test_invalid_characters(self):
        ''' test invalid characters in project name. '''
        with pytest.raises(ValidationError, match="cannot contain"):
            ProjectInput(project="project/name")

    def test_whitespace_trimming(self):
        ''' test that whitespace is trimmed. '''
        valid_input = ProjectInput(project="  my-project  ")
        assert valid_input.project == "my-project"
