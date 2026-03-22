'''
Pydantic validation models for Obsidian MCP input validation.
'''

import re
from typing import Any, Dict

from pydantic import BaseModel, field_validator


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


class FilePathInput(BaseModel):
    '''Input validation for file path operations.'''
    file_path: str

    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        if not v or v.strip() == '':
            raise ValueError('File path cannot be empty')
        if '..' in v or v.startswith('/'):
            raise ValueError('Invalid file path: directory traversal not allowed')
        return v.strip()


class FileWriteInput(BaseModel):
    '''Input validation for file write operations.'''
    file_path: str
    content: str

    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        if not v or v.strip() == '':
            raise ValueError('File path cannot be empty')
        if '..' in v or v.startswith('/'):
            raise ValueError('Invalid file path: directory traversal not allowed')
        return v.strip()


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
        return v


def create_error_response(message: str) -> Dict[str, Any]:
    '''Create a standardized error response.'''
    return {'error': message, 'success': False}


def create_success_response() -> Dict[str, bool]:
    '''Create a standardized success response.'''
    return {'success': True}
