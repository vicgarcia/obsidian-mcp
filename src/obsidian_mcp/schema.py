'''
Pydantic validation models for Obsidian MCP input validation.
'''

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, field_validator, model_validator


class YearMonthInput(BaseModel):
    '''Input validation for year/month operations.'''
    year: str
    month: str

    @field_validator('year')
    @classmethod
    def validate_year(cls, v: str) -> str:
        if not re.match(r'^\d{4}$', v):
            raise ValueError('Year must be in YYYY format')
        year_int = int(v)
        if year_int < 1970 or year_int > 2100:
            raise ValueError('Year must be between 1970 and 2100')
        return v

    @field_validator('month')
    @classmethod
    def validate_month(cls, v: str) -> str:
        if not re.match(r'^\d{2}$', v):
            raise ValueError('Month must be in MM format (01-12)')
        month_int = int(v)
        if month_int < 1 or month_int > 12:
            raise ValueError('Month must be between 01 and 12')
        return v


def _validate_journal_date(v: str) -> str:
    '''Validate a YYYY-MM-DD journal date string.'''
    v = v.strip()
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
        raise ValueError('Date must be in YYYY-MM-DD format')
    try:
        datetime.strptime(v, '%Y-%m-%d')
    except ValueError:
        raise ValueError('Date is not a valid calendar date')
    return v


class JournalDateInput(BaseModel):
    '''Input validation for a journal entry date.'''
    date: str

    @field_validator('date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        return _validate_journal_date(v)


class JournalTextInput(BaseModel):
    '''
    Input validation for appending or prepending to a journal entry (date defaults to today).

    The text is kept exactly as given, whitespace and newlines included.
    '''
    text: str
    date: Optional[str] = None

    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        if v == '':
            raise ValueError('Text cannot be empty')
        return v

    @field_validator('date')
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else _validate_journal_date(v)

    def entry_date(self) -> Optional[datetime]:
        '''The parsed entry date, or None for today.'''
        return None if self.date is None else datetime.strptime(self.date, '%Y-%m-%d')


class JournalNoteInput(BaseModel):
    '''
    Input validation for adding a note to a journal entry (date defaults to today).

    The note is trimmed and must start with a ### heading. The rest of its layout is
    guidance in the tool description, not checked here.
    '''
    text: str
    date: Optional[str] = None

    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Note cannot be empty')
        if not v.startswith('### '):
            raise ValueError('Note must start with a ### heading')
        return v

    @field_validator('date')
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else _validate_journal_date(v)

    def entry_date(self) -> Optional[datetime]:
        '''The parsed entry date, or None for today.'''
        return None if self.date is None else datetime.strptime(self.date, '%Y-%m-%d')


class JournalWriteInput(BaseModel):
    '''Input validation for writing a whole journal entry (date defaults to today).'''
    content: str
    date: Optional[str] = None

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or v.strip() == '':
            raise ValueError('Content cannot be empty')
        return v

    @field_validator('date')
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else _validate_journal_date(v)

    def entry_date(self) -> Optional[datetime]:
        '''The parsed entry date, or None for today.'''
        return None if self.date is None else datetime.strptime(self.date, '%Y-%m-%d')


# a "quoted phrase" or a single word
_QUERY_TERM = re.compile(r'"([^"]*)"|(\S+)')

MAX_QUERY_LENGTH = 200
MAX_SEARCH_RESULTS = 50


def parse_search_terms(query: str) -> List[str]:
    '''
    Split a search query into lowercase terms.

    Words are separate terms; text in double quotes is kept together as one phrase. An
    unmatched quote is treated as part of a word.
    '''
    terms = []
    for phrase, word in _QUERY_TERM.findall(query):
        term = ' '.join((phrase if phrase else word).split()).casefold()
        if term:
            terms.append(term)
    return terms


class JournalSearchInput(BaseModel):
    '''Input validation for searching the journal.'''
    query: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_results: int = 20

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Query cannot be empty')
        if len(v) > MAX_QUERY_LENGTH:
            raise ValueError(f'Query cannot be longer than {MAX_QUERY_LENGTH} characters')
        if not parse_search_terms(v):
            raise ValueError('Query must contain at least one word')
        return v

    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else _validate_journal_date(v)

    @field_validator('max_results')
    @classmethod
    def validate_max_results(cls, v: int) -> int:
        if v < 1 or v > MAX_SEARCH_RESULTS:
            raise ValueError(f'max_results must be between 1 and {MAX_SEARCH_RESULTS}')
        return v

    @model_validator(mode='after')
    def validate_range(self) -> 'JournalSearchInput':
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError('start_date cannot be after end_date')
        return self

    def terms(self) -> List[str]:
        '''The query split into lowercase terms.'''
        return parse_search_terms(self.query)


# names windows treats as devices, with or without an extension (nul.md is nul), any case;
# the superscript digits count too
_RESERVED_NAMES = re.compile(r'^(con|prn|aux|nul|conin\$|conout\$|(com|lpt)[0-9¹²³])$', re.IGNORECASE)
# characters windows doesn't allow in a name, and control characters (a nul byte included)
_BAD_NAME_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')


def check_name(name: str, what: str = 'Path') -> None:
    '''
    Reject a file or folder name that is unsafe or unportable on any platform.

    The vault syncs between macOS and Windows, so names Windows can't hold are refused on
    both: reserved device names, characters like : and ?, and a trailing dot or space,
    which Windows silently drops (x.md. would name x.md).
    '''
    if _BAD_NAME_CHARS.search(name):
        raise ValueError(f'{what} cannot contain < > : " | ? * or control characters')
    if _RESERVED_NAMES.match(name.split('.', 1)[0].rstrip(' ')):
        raise ValueError(f'{what} cannot use a reserved device name: {name}')
    if name.endswith(('.', ' ')):
        raise ValueError(f'{what} parts cannot end with a dot or space: {name}')


def validate_vault_path(v: str) -> str:
    '''
    Validate a vault-relative path and return it with forward slashes.

    The same rules on every platform, checked on the text alone before anything touches
    the disk: no absolute, rooted, UNC or drive paths, no .. or . parts, no empty parts,
    and every part a portable name (check_name). A backslash counts as a separator, so
    windows-style input is checked the same way. VaultClient still resolves the result
    and refuses anything that lands outside the vault, which covers links.
    '''
    if not v or v.strip() == '':
        raise ValueError('File path cannot be empty')
    path = v.strip().replace('\\', '/')
    if path.startswith('/'):
        raise ValueError('Invalid file path: directory traversal not allowed (absolute or rooted path)')
    parts = path.split('/')
    if any(part in ('', '.', '..') for part in parts):
        if '..' in parts:
            raise ValueError('Invalid file path: directory traversal not allowed (..)')
        raise ValueError('Invalid file path: empty or . parts are not allowed')
    for part in parts:
        check_name(part)
    return path


class FilePathInput(BaseModel):
    '''Input validation for file path operations.'''
    file_path: str

    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        return validate_vault_path(v)


class FileWriteInput(BaseModel):
    '''Input validation for file write operations.'''
    file_path: str
    content: str

    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        return validate_vault_path(v)


class ProjectInput(BaseModel):
    '''Input validation for project operations.'''
    project: str

    @field_validator('project')
    @classmethod
    def validate_project(cls, v: str) -> str:
        if not v or v.strip() == '':
            raise ValueError('Project name cannot be empty')
        v = v.strip()
        invalid_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
        for char in invalid_chars:
            if char in v:
                raise ValueError(f"Project name cannot contain '{char}'")
        if '..' in v:
            raise ValueError("Project name cannot contain '..'")
        check_name(v, 'Project name')
        return v


def create_error_response(message: str) -> Dict[str, Any]:
    '''Create a standardized error response.'''
    return {'error': message, 'success': False}


def create_success_response() -> Dict[str, bool]:
    '''Create a standardized success response.'''
    return {'success': True}
