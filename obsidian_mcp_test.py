import os
import pytest
from datetime import datetime
from pathlib import Path
from pydantic import ValidationError

from obsidian_mcp import (
    # tools
    read_file,
    write_file,
    get_current_date,
    list_projects,
    list_project_content,
    create_project,
    list_wiki,
    # models
    YearMonthInput,
    FilePathInput,
    FileWriteInput,
    ProjectInput,
    # utilities
    get_vault_base,
    validate_vault_path,
    create_error_response,
    create_success_response,
    create_file_info,
    get_today_journal_path,
    list_files_in_directory,
    list_directories_in_directory,
)


# fixtures

TEST_VAULT_PATH = Path(__file__).parent / "tests" / "fixtures" / "vault"


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    ''' set up the test environment with the test vault path. '''
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(TEST_VAULT_PATH.absolute()))


@pytest.fixture
def vault_path():
    ''' return the test vault path. '''
    return TEST_VAULT_PATH


@pytest.fixture
def setup_wiki(vault_path):
    ''' create sample wiki articles for testing. '''
    wiki_dir = vault_path / "wiki"
    wiki_dir.mkdir(parents=True, exist_ok=True)

    for existing_file in wiki_dir.glob("*"):
        if existing_file.is_file():
            existing_file.unlink()

    articles = {
        "python-asyncio.md": "# Python Asyncio\n\nComplete guide to async programming.",
        "docker-networking.md": "# Docker Networking\n\nNetworking concepts in Docker.",
        "git-workflows.md": "# Git Workflows\n\nBranching strategies and workflows.",
    }

    for filename, content in articles.items():
        (wiki_dir / filename).write_text(content)

    yield wiki_dir

    for existing_file in wiki_dir.glob("*"):
        if existing_file.is_file():
            existing_file.unlink()


# file operations tests

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

        test_file = vault_path / "test" / "new_file.md"
        assert test_file.exists()
        assert test_file.read_text() == test_content

    def test_write_file_creates_directories(self, vault_path):
        ''' test that write_file creates parent directories. '''
        test_content = "# Deep Test\n\nNested content."
        result = write_file("deep/nested/path/test.md", test_content)

        assert result == {"success": True}

        test_file = vault_path / "deep" / "nested" / "path" / "test.md"
        assert test_file.exists()
        assert test_file.parent.exists()

    def test_write_file_path_traversal(self):
        ''' test that path traversal is prevented in write operations. '''
        result = write_file("../../../tmp/evil.txt", "evil content")

        assert "error" in result
        assert "Invalid input" in result["error"]


# journal tests

class TestJournalTools:
    ''' test journal-related tools. '''

    def test_get_current_date(self):
        ''' test getting current date. '''
        result = get_current_date()

        assert isinstance(result, dict)
        assert "formatted" in result
        assert "human" in result

        formatted = result["formatted"]
        assert len(formatted) == 10
        assert formatted[4] == "-"
        assert formatted[7] == "-"

        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert formatted == expected_date

    def test_list_todays_journal_entry(self):
        ''' test getting today's journal entry path. '''
        result_path = get_today_journal_path()
        assert result_path.startswith("journal/")
        assert result_path.endswith(".md")

    def test_list_journal_entries_by_year_and_month(self, vault_path):
        ''' test listing journal entries for a specific month. '''
        test_dir = vault_path / "journal" / "2025" / "01"
        test_dir.mkdir(parents=True, exist_ok=True)

        (test_dir / "2025-01-16.md").write_text("# Jan 16\nContent")
        (test_dir / "2025-01-17.md").write_text("# Jan 17\nContent")

        files = list_files_in_directory(test_dir, vault_path)

        assert len(files) >= 2
        assert any(f["name"] == "2025-01-15.md" for f in files)


# project tests

class TestProjectTools:
    ''' test project management tools. '''

    def test_create_and_list_projects(self, vault_path):
        ''' test creating and listing projects. '''
        projects_dir = vault_path / "projects"
        (projects_dir / "test-project").mkdir(parents=True, exist_ok=True)
        (projects_dir / "another-project").mkdir(parents=True, exist_ok=True)

        projects = list_directories_in_directory(projects_dir, vault_path)

        project_names = [p["name"] for p in projects]
        assert "test-project" in project_names
        assert "another-project" in project_names

    def test_list_project_content(self, vault_path):
        ''' test listing content within a project. '''
        project_dir = vault_path / "projects" / "website-redesign"
        project_dir.mkdir(parents=True, exist_ok=True)

        (project_dir / "requirements.md").write_text("# Requirements\nContent")
        (project_dir / "design.md").write_text("# Design\nContent")

        files = list_files_in_directory(project_dir, vault_path, recursive=True)

        file_names = [f["name"] for f in files]
        assert "requirements.md" in file_names
        assert "design.md" in file_names

    def test_list_projects_tool(self, vault_path):
        ''' test the list_projects tool. '''
        projects_dir = vault_path / "projects"
        (projects_dir / "test-project").mkdir(parents=True, exist_ok=True)

        result = list_projects()

        assert isinstance(result, list)
        project_names = [p["name"] for p in result if "name" in p]
        assert "test-project" in project_names

    def test_list_project_content_tool(self, vault_path):
        ''' test the list_project_content tool. '''
        project_dir = vault_path / "projects" / "website-redesign"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "requirements.md").write_text("# Requirements")
        (project_dir / "design.md").write_text("# Design")

        result = list_project_content("website-redesign")

        assert isinstance(result, list)
        file_names = [f["name"] for f in result if "name" in f]
        assert "requirements.md" in file_names
        assert "design.md" in file_names

    def test_create_project_tool(self, vault_path):
        ''' test the create_project tool. '''
        result = create_project("new-test-project")

        assert result == {"success": True}

        project_dir = vault_path / "projects" / "new-test-project"
        assert project_dir.exists()
        assert project_dir.is_dir()


# wiki tests

class TestWikiTools:
    ''' test wiki management tools. '''

    def test_list_wiki_empty(self, vault_path):
        ''' test listing wiki articles when directory is empty. '''
        wiki_dir = vault_path / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)

        for existing_file in wiki_dir.glob("*"):
            if existing_file.is_file():
                existing_file.unlink()

        result = list_wiki()

        assert isinstance(result, list)
        assert len(result) == 0

    def test_list_wiki_with_content(self, setup_wiki):
        ''' test listing wiki articles when articles exist. '''
        result = list_wiki()

        assert isinstance(result, list)
        assert len(result) == 3

        article_names = [a["name"] for a in result]
        assert "python-asyncio.md" in article_names
        assert "docker-networking.md" in article_names
        assert "git-workflows.md" in article_names

        article_paths = [a["path"] for a in result]
        assert "wiki/python-asyncio.md" in article_paths

    def test_list_wiki_filters_markdown(self, vault_path):
        ''' test that non-markdown files are filtered out. '''
        wiki_dir = vault_path / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)

        for existing_file in wiki_dir.glob("*"):
            if existing_file.is_file():
                existing_file.unlink()

        (wiki_dir / "guide.md").write_text("# Guide")
        (wiki_dir / "image.png").write_bytes(b"fake image data")
        (wiki_dir / "data.json").write_text('{"key": "value"}')

        result = list_wiki()

        assert len(result) == 1
        assert result[0]["name"] == "guide.md"

        (wiki_dir / "guide.md").unlink()
        (wiki_dir / "image.png").unlink()
        (wiki_dir / "data.json").unlink()

    def test_read_wiki_article(self, setup_wiki):
        ''' test reading a wiki article using read_file. '''
        result = read_file("wiki/python-asyncio.md")

        assert "content" in result
        assert "Python Asyncio" in result["content"]
        assert "async programming" in result["content"]

    def test_write_wiki_article(self, vault_path):
        ''' test writing a new wiki article using write_file. '''
        wiki_dir = vault_path / "wiki"
        wiki_dir.mkdir(parents=True, exist_ok=True)

        content = "# Kubernetes Basics\n\nIntroduction to Kubernetes concepts."
        result = write_file("wiki/kubernetes-basics.md", content)

        assert result == {"success": True}

        article_file = wiki_dir / "kubernetes-basics.md"
        assert article_file.exists()
        assert article_file.read_text() == content

        articles = list_wiki()
        article_names = [a["name"] for a in articles]
        assert "kubernetes-basics.md" in article_names

        article_file.unlink()


# model validation tests

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


# utility function tests

class TestVaultOperations:
    ''' test vault path operations. '''

    def test_get_vault_base(self, vault_path):
        ''' test getting vault base path. '''
        base = get_vault_base()
        assert base.exists()
        assert base.is_dir()
        assert "vault" in str(base)

    def test_validate_vault_path_valid(self, vault_path):
        ''' test validating a valid vault path. '''
        valid_path = validate_vault_path("journal/2025/01/test.md")
        assert valid_path.is_relative_to(vault_path)

    def test_validate_vault_path_traversal(self, vault_path):
        ''' test that directory traversal is prevented. '''
        test_path = validate_vault_path("journal/test.md")
        assert test_path.is_relative_to(vault_path)

    def test_validate_vault_path_absolute(self):
        ''' test that absolute paths are prevented. '''
        with pytest.raises(ValueError, match="outside vault directory"):
            validate_vault_path("/etc/passwd")


class TestResponseHelpers:
    ''' test response helper functions. '''

    def test_create_error_response(self):
        ''' test creating error responses. '''
        error = create_error_response("Test error message")
        assert error == {"error": "Test error message", "success": False}

    def test_create_success_response(self):
        ''' test creating success responses. '''
        success = create_success_response()
        assert success == {"success": True}


class TestFileHelpers:
    ''' test file helper functions. '''

    def test_create_file_info(self, vault_path):
        ''' test creating file info objects. '''
        test_file = vault_path / "journal" / "2025" / "01" / "2025-01-15.md"
        file_info = create_file_info(test_file, vault_path)

        assert file_info["name"] == "2025-01-15.md"
        assert file_info["path"] == "journal/2025/01/2025-01-15.md"

    def test_get_today_journal_path(self):
        ''' test getting today's journal path. '''
        journal_path = get_today_journal_path()

        assert journal_path.startswith("journal/")
        assert journal_path.endswith(".md")

        today = datetime.now()
        assert str(today.year) in journal_path
        assert f"{today.month:02d}" in journal_path
        assert f"{today.day:02d}" in journal_path


class TestDirectoryListing:
    ''' test directory listing functions. '''

    def test_list_files_in_directory_existing(self, vault_path):
        ''' test listing files in an existing directory. '''
        journal_dir = vault_path / "journal" / "2025" / "01"
        files = list_files_in_directory(journal_dir, vault_path)

        assert len(files) > 0
        assert any(f["name"] == "2025-01-15.md" for f in files)

    def test_list_files_in_directory_nonexistent(self, vault_path):
        ''' test listing files in a non-existent directory. '''
        nonexistent_dir = vault_path / "nonexistent"
        files = list_files_in_directory(nonexistent_dir, vault_path)

        assert files == []

    def test_list_files_in_directory_recursive(self, vault_path):
        ''' test recursive file listing. '''
        journal_dir = vault_path / "journal"
        files = list_files_in_directory(journal_dir, vault_path, recursive=True)

        assert len(files) > 0
        assert any("2025/01" in f["path"] for f in files)


# integration tests

class TestIntegration:
    ''' integration tests combining multiple operations. '''

    def test_full_workflow_journal(self, vault_path):
        ''' test a complete journal workflow. '''
        today_path = f"journal/2025/01/2025-01-20.md"
        content = "# January 20, 2025\n\n## Notes\nTest entry"

        result = write_file(today_path, content)
        assert result == {"success": True}

        result = read_file(today_path)
        assert "content" in result
        assert "January 20, 2025" in result["content"]

        jan_dir = vault_path / "journal" / "2025" / "01"
        files = list_files_in_directory(jan_dir, vault_path)

        assert any(f["name"] == "2025-01-20.md" for f in files)

    def test_full_workflow_projects(self, vault_path):
        ''' test a complete project workflow. '''
        result = create_project("test-workflow-project")
        assert result == {"success": True}

        content = "# Project Overview\n\nProject details here."
        result = write_file("projects/test-workflow-project/overview.md", content)
        assert result == {"success": True}

        result = read_file("projects/test-workflow-project/overview.md")
        assert "Project Overview" in result["content"]

        result = list_projects()
        project_names = [p["name"] for p in result if "name" in p]
        assert "test-workflow-project" in project_names
