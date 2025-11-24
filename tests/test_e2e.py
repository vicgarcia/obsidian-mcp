import pytest
from pathlib import Path
from datetime import datetime

from obsidian_mcp.server import read_file, write_file, get_current_date, list_projects, list_project_content, create_project, list_knowledge_content


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

    def test_get_current_date(self):
        ''' test getting current date. '''
        result = get_current_date()

        # verify format is YYYY-MM-DD
        assert isinstance(result, str)
        assert len(result) == 10
        assert result[4] == "-"
        assert result[7] == "-"

        # verify it matches today's date
        expected_date = datetime.now().strftime("%Y-%m-%d")
        assert result == expected_date

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


class TestProjectTools:
    ''' test project management tools. '''

    def test_create_and_list_projects(self, vault_path):
        ''' test creating and listing projects. '''
        # create test projects
        projects_dir = vault_path / "projects"
        (projects_dir / "test-project").mkdir(parents=True, exist_ok=True)
        (projects_dir / "another-project").mkdir(parents=True, exist_ok=True)

        # test listing projects
        from obsidian_mcp.utils import list_directories_in_directory
        projects = list_directories_in_directory(projects_dir, vault_path)

        project_names = [p["name"] for p in projects]
        assert "test-project" in project_names
        assert "another-project" in project_names

    def test_list_project_content(self, vault_path):
        ''' test listing content within a project. '''
        # create test project with content
        project_dir = vault_path / "projects" / "website-redesign"
        project_dir.mkdir(parents=True, exist_ok=True)

        (project_dir / "requirements.md").write_text("# Requirements\nContent")
        (project_dir / "design.md").write_text("# Design\nContent")

        from obsidian_mcp.utils import list_files_in_directory
        files = list_files_in_directory(project_dir, vault_path, recursive=True)

        file_names = [f["name"] for f in files]
        assert "requirements.md" in file_names
        assert "design.md" in file_names

    def test_list_projects_tool(self, vault_path):
        ''' test the list_projects tool. '''
        # create a test project
        projects_dir = vault_path / "projects"
        (projects_dir / "test-project").mkdir(parents=True, exist_ok=True)

        result = list_projects()

        assert isinstance(result, list)
        project_names = [p["name"] for p in result if "name" in p]
        assert "test-project" in project_names

    def test_list_project_content_tool(self, vault_path):
        ''' test the list_project_content tool. '''
        # ensure website-redesign project exists with files
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

        # verify project was created
        project_dir = vault_path / "projects" / "new-test-project"
        assert project_dir.exists()
        assert project_dir.is_dir()


class TestKnowledgeTools:
    ''' test knowledge management tools. '''

    def test_list_knowledge_content_empty(self, vault_path):
        ''' test listing knowledge guides when directory is empty. '''
        # ensure knowledge directory exists but is empty
        knowledge_dir = vault_path / "knowledge"
        knowledge_dir.mkdir(parents=True, exist_ok=True)

        # clean any existing files
        for existing_file in knowledge_dir.glob("*"):
            if existing_file.is_file():
                existing_file.unlink()

        result = list_knowledge_content()

        assert isinstance(result, list)
        assert len(result) == 0

    def test_list_knowledge_content_with_content(self, setup_knowledge_guides):
        ''' test listing knowledge guides when guides exist. '''
        result = list_knowledge_content()

        assert isinstance(result, list)
        assert len(result) == 3

        guide_names = [g["name"] for g in result]
        assert "python-asyncio.md" in guide_names
        assert "docker-networking.md" in guide_names
        assert "git-workflows.md" in guide_names

        # verify paths are correct
        guide_paths = [g["path"] for g in result]
        assert "knowledge/python-asyncio.md" in guide_paths

    def test_list_knowledge_content_filters_markdown(self, vault_path):
        ''' test that non-markdown files are filtered out. '''
        knowledge_dir = vault_path / "knowledge"
        knowledge_dir.mkdir(parents=True, exist_ok=True)

        # clean any existing files
        for existing_file in knowledge_dir.glob("*"):
            if existing_file.is_file():
                existing_file.unlink()

        # create markdown and non-markdown files
        (knowledge_dir / "guide.md").write_text("# Guide")
        (knowledge_dir / "image.png").write_bytes(b"fake image data")
        (knowledge_dir / "data.json").write_text('{"key": "value"}')

        result = list_knowledge_content()

        assert len(result) == 1
        assert result[0]["name"] == "guide.md"

        # cleanup
        (knowledge_dir / "guide.md").unlink()
        (knowledge_dir / "image.png").unlink()
        (knowledge_dir / "data.json").unlink()

    def test_read_knowledge_guide(self, setup_knowledge_guides):
        ''' test reading a knowledge guide using read_file. '''
        result = read_file("knowledge/python-asyncio.md")

        assert "content" in result
        assert "Python Asyncio" in result["content"]
        assert "async programming" in result["content"]

    def test_write_knowledge_guide(self, vault_path):
        ''' test writing a new knowledge guide using write_file. '''
        knowledge_dir = vault_path / "knowledge"
        knowledge_dir.mkdir(parents=True, exist_ok=True)

        content = "# Kubernetes Basics\n\nIntroduction to Kubernetes concepts."
        result = write_file("knowledge/kubernetes-basics.md", content)

        assert result == {"success": True}

        # verify file was created
        guide_file = knowledge_dir / "kubernetes-basics.md"
        assert guide_file.exists()
        assert guide_file.read_text() == content

        # verify it appears in listing
        guides = list_knowledge_content()
        guide_names = [g["name"] for g in guides]
        assert "kubernetes-basics.md" in guide_names

        # cleanup
        guide_file.unlink()


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

    def test_full_workflow_projects(self, vault_path):
        ''' test a complete project workflow. '''
        # 1. create a project directory
        result = create_project("test-workflow-project")
        assert result == {"success": True}

        # 2. add content to the project
        content = "# Project Overview\n\nProject details here."
        result = write_file("projects/test-workflow-project/overview.md", content)
        assert result == {"success": True}

        # 3. read the content back
        result = read_file("projects/test-workflow-project/overview.md")
        assert "Project Overview" in result["content"]

        # 4. verify project listing
        result = list_projects()
        project_names = [p["name"] for p in result if "name" in p]
        assert "test-workflow-project" in project_names
