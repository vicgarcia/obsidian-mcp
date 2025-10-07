import re
from datetime import datetime

from pydantic import BaseModel, field_validator


class JournalDateInput(BaseModel):
    ''' Input validation for journal date operations. '''
    date: str

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        ''' Validate YYYY-MM-DD format. '''
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', v):
            raise ValueError("Date must be in YYYY-MM-DD format")

        # validate that it's a real date
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid date")

        return v


class YearMonthInput(BaseModel):
    ''' Input validation for year/month operations. '''
    year: str
    month: str

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: str) -> str:
        ''' Validate YYYY format. '''
        if not re.match(r'^\d{4}$', v):
            raise ValueError("Year must be in YYYY format")

        year_int = int(v)
        if year_int < 1970 or year_int > 2100:
            raise ValueError("Year must be between 1970 and 2100")

        return v

    @field_validator("month")
    @classmethod
    def validate_month(cls, v: str) -> str:
        ''' Validate MM format. '''
        if not re.match(r'^\d{2}$', v):
            raise ValueError("Month must be in MM format (01-12)")

        month_int = int(v)
        if month_int < 1 or month_int > 12:
            raise ValueError("Month must be between 01 and 12")

        return v


class FilePathInput(BaseModel):
    ''' Input validation for file path operations. '''
    file_path: str

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        ''' Validate file path format and security. '''
        if not v or v.strip() == "":
            raise ValueError("File path cannot be empty")

        # prevent directory traversal
        if ".." in v or v.startswith("/"):
            raise ValueError("Invalid file path: directory traversal not allowed")

        return v.strip()


class FileWriteInput(BaseModel):
    ''' Input validation for file write operations. '''
    file_path: str
    content: str

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        ''' Validate file path format and security. '''
        if not v or v.strip() == "":
            raise ValueError("File path cannot be empty")

        # prevent directory traversal
        if ".." in v or v.startswith("/"):
            raise ValueError("Invalid file path: directory traversal not allowed")

        return v.strip()


class ProjectInput(BaseModel):
    ''' Input validation for project operations. '''
    project: str

    @field_validator("project")
    @classmethod
    def validate_project(cls, v: str) -> str:
        ''' Validate project name format. '''
        if not v or v.strip() == "":
            raise ValueError("Project name cannot be empty")

        # remove leading/trailing whitespace
        v = v.strip()

        # check for invalid characters that could cause path issues
        invalid_chars = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]
        for char in invalid_chars:
            if char in v:
                raise ValueError(f"Project name cannot contain '{char}'")

        # prevent directory traversal
        if ".." in v:
            raise ValueError("Project name cannot contain '..'")

        return v
