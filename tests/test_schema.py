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
    validate_vault_path,
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

    def test_create_success_response(self):
        '''Test creating success responses.'''
        success = create_success_response()
        assert success == {'success': True}


class TestVaultPath:
    '''Vault-relative path rules, checked on the text and the same on every platform.'''

    @pytest.mark.parametrize('path, expected', [
        ('journal/2025/01/2025-01-15.md', 'journal/2025/01/2025-01-15.md'),
        ('projects/home automation/plan.md', 'projects/home automation/plan.md'),
        ('projects\\garage\\plan.md', 'projects/garage/plan.md'),
        ('  wiki/docker networking.md  ', 'wiki/docker networking.md'),
        ('projects/p/notes..md', 'projects/p/notes..md'),
        ('projects/p/.obsidian-ish', 'projects/p/.obsidian-ish'),
        ('projects/p/console.md', 'projects/p/console.md'),
        ('projects/p/nullable.md', 'projects/p/nullable.md'),
        ('projects/p/com10.md', 'projects/p/com10.md'),
        ('projects/p/café ünïcode.md', 'projects/p/café ünïcode.md'),
    ])
    def test_accepts_portable_relative_paths(self, path, expected):
        assert validate_vault_path(path) == expected

    @pytest.mark.parametrize('path', [
        '../outside.md',
        'projects/../../outside.md',
        '..\\outside.md',
        'projects\\..\\..\\outside.md',
        'projects/p/..',
    ])
    def test_rejects_dotdot(self, path):
        with pytest.raises(ValueError, match='directory traversal'):
            validate_vault_path(path)

    @pytest.mark.parametrize('path', [
        '/etc/passwd',
        '\\Windows\\system.ini',
        '\\\\server\\share\\x.md',
        '//server/share/x.md',
        '\\\\?\\C:\\x.md',
    ])
    def test_rejects_absolute_rooted_and_unc(self, path):
        with pytest.raises(ValueError, match='absolute or rooted'):
            validate_vault_path(path)

    @pytest.mark.parametrize('path', [
        'C:\\Windows\\system.ini',
        'C:/Windows/system.ini',
        'C:Users\\x.md',
        'D:secret.md',
        'journal/x.md:hidden',
        'journal/x.md::$DATA',
        'projects/a?b.md',
        'projects/a*.md',
        'projects/a<b>.md',
        'projects/a|b.md',
        'projects/"quoted".md',
        'projects/a\x00.md',
        'projects/a\nb.md',
    ])
    def test_rejects_drives_streams_and_bad_characters(self, path):
        with pytest.raises(ValueError, match='cannot contain'):
            validate_vault_path(path)

    @pytest.mark.parametrize('path', [
        'projects/CON', 'projects/con.md', 'projects/NUL.md', 'projects/nul.tar.gz', 'projects/Aux',
        'projects/prn.txt', 'projects/COM1', 'projects/lpt9.md', 'projects/com¹.md', 'projects/conin$',
        'CON/x.md', 'projects/nul .md',
    ])
    def test_rejects_reserved_device_names(self, path):
        with pytest.raises(ValueError, match='reserved device name'):
            validate_vault_path(path)

    @pytest.mark.parametrize('path', ['projects/x.md.', 'projects/dir./x.md', 'projects/dir /x.md'])
    def test_rejects_trailing_dot_or_space(self, path):
        with pytest.raises(ValueError, match='end with a dot or space'):
            validate_vault_path(path)

    @pytest.mark.parametrize('path', ['projects//x.md', 'projects/./x.md', './x.md', 'projects/'])
    def test_rejects_empty_and_dot_parts(self, path):
        with pytest.raises(ValueError, match='empty or . parts'):
            validate_vault_path(path)

    @pytest.mark.parametrize('path', ['', '   '])
    def test_rejects_empty(self, path):
        with pytest.raises(ValueError, match='cannot be empty'):
            validate_vault_path(path)

    @pytest.mark.parametrize('name', ['NUL', 'com3', 'a:b', 'x.'])
    def test_project_names_follow_the_same_name_rules(self, name):
        with pytest.raises(ValidationError):
            ProjectInput(project=name)
