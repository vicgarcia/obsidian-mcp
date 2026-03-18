'''
Tests for Pydantic validation models.
'''

import pytest
from pydantic import ValidationError

from obsidian_mcp.schema import (
    YearMonthInput,
    FilePathInput,
    FileWriteInput,
    ProjectInput,
    create_error_response,
    create_success_response,
)


class TestYearMonthInput:
    '''Test year/month validation.'''

    def test_valid_year_month(self):
        '''Test valid year and month.'''
        valid_input = YearMonthInput(year='2025', month='01')
        assert valid_input.year == '2025'
        assert valid_input.month == '01'

    def test_invalid_year_format(self):
        '''Test invalid year format.'''
        with pytest.raises(ValidationError, match='YYYY format'):
            YearMonthInput(year='25', month='01')

    def test_invalid_year_range(self):
        '''Test invalid year range.'''
        with pytest.raises(ValidationError, match='between 1970 and 2100'):
            YearMonthInput(year='1969', month='01')

    def test_invalid_month_format(self):
        '''Test invalid month format.'''
        with pytest.raises(ValidationError, match='MM format'):
            YearMonthInput(year='2025', month='1')

    def test_invalid_month_range(self):
        '''Test invalid month range.'''
        with pytest.raises(ValidationError, match='between 01 and 12'):
            YearMonthInput(year='2025', month='13')


class TestFilePathInput:
    '''Test file path validation.'''

    def test_valid_path(self):
        '''Test valid file path.'''
        valid_input = FilePathInput(file_path='journal/2025/01/test.md')
        assert valid_input.file_path == 'journal/2025/01/test.md'

    def test_empty_path(self):
        '''Test empty file path.'''
        with pytest.raises(ValidationError, match='cannot be empty'):
            FilePathInput(file_path='')

    def test_whitespace_path(self):
        '''Test whitespace file path.'''
        with pytest.raises(ValidationError, match='cannot be empty'):
            FilePathInput(file_path='   ')

    def test_directory_traversal_dotdot(self):
        '''Test directory traversal with .. is prevented.'''
        with pytest.raises(ValidationError, match='directory traversal'):
            FilePathInput(file_path='../../../etc/passwd')

    def test_directory_traversal_absolute(self):
        '''Test absolute path is prevented.'''
        with pytest.raises(ValidationError, match='directory traversal'):
            FilePathInput(file_path='/etc/passwd')

    def test_path_trimming(self):
        '''Test that paths are trimmed.'''
        valid_input = FilePathInput(file_path='  journal/test.md  ')
        assert valid_input.file_path == 'journal/test.md'


class TestFileWriteInput:
    '''Test file write input validation.'''

    def test_valid_input(self):
        '''Test valid file write input.'''
        valid_input = FileWriteInput(file_path='test.md', content='# Test')
        assert valid_input.file_path == 'test.md'
        assert valid_input.content == '# Test'

    def test_empty_path(self):
        '''Test empty file path.'''
        with pytest.raises(ValidationError, match='cannot be empty'):
            FileWriteInput(file_path='', content='# Test')

    def test_directory_traversal(self):
        '''Test directory traversal is prevented.'''
        with pytest.raises(ValidationError, match='directory traversal'):
            FileWriteInput(file_path='../evil.txt', content='evil')


class TestProjectInput:
    '''Test project name validation.'''

    def test_valid_project(self):
        '''Test valid project name.'''
        valid_input = ProjectInput(project='my-project')
        assert valid_input.project == 'my-project'

    def test_valid_project_with_spaces(self):
        '''Test valid project name with spaces.'''
        valid_input = ProjectInput(project='home automation')
        assert valid_input.project == 'home automation'

    def test_empty_project(self):
        '''Test empty project name.'''
        with pytest.raises(ValidationError, match='cannot be empty'):
            ProjectInput(project='')

    def test_directory_traversal(self):
        '''Test directory traversal is prevented.'''
        with pytest.raises(ValidationError, match='cannot contain'):
            ProjectInput(project='../etc')

    def test_invalid_slash(self):
        '''Test slash in project name.'''
        with pytest.raises(ValidationError, match='cannot contain'):
            ProjectInput(project='project/name')

    def test_invalid_backslash(self):
        '''Test backslash in project name.'''
        with pytest.raises(ValidationError, match='cannot contain'):
            ProjectInput(project='project\\name')

    def test_invalid_colon(self):
        '''Test colon in project name.'''
        with pytest.raises(ValidationError, match='cannot contain'):
            ProjectInput(project='project:name')

    def test_whitespace_trimming(self):
        '''Test that whitespace is trimmed.'''
        valid_input = ProjectInput(project='  my-project  ')
        assert valid_input.project == 'my-project'


class TestResponseHelpers:
    '''Test response helper functions.'''

    def test_create_error_response(self):
        '''Test creating error responses.'''
        error = create_error_response('Test error message')
        assert error == {'error': 'Test error message', 'success': False}

    def test_create_success_response(self):
        '''Test creating success responses.'''
        success = create_success_response()
        assert success == {'success': True}
