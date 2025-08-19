"""End-to-end tests for the Obsidian MCP server."""

import pytest
from pathlib import Path

from obsidian_mcp.server import read_file, write_file
from obsidian_mcp.journal import register_journal_tools
from obsidian_mcp.knowledge import register_knowledge_tools
from obsidian_mcp.projects import register_projects_tools


class TestFileOperations:
    """Test core file operations."""
    
    def test_read_existing_file(self, vault_path):
        """Test reading an existing file."""
        result = read_file("journal/2025/01/2025-01-15.md")
        
        assert "content" in result
        assert "January 15, 2025" in result["content"]
        assert "#journal" in result["content"]
    
    def test_read_nonexistent_file(self):
        """Test reading a non-existent file."""
        result = read_file("nonexistent/file.md")
        
        assert "error" in result
        assert "File not found" in result["error"]
    
    def test_read_file_path_traversal(self):
        """Test that path traversal is prevented in read operations."""
        result = read_file("../../../etc/passwd")
        
        assert "error" in result
        assert "Invalid input" in result["error"]
    
    def test_write_new_file(self, vault_path):
        """Test writing a new file."""
        test_content = "# Test Note\n\nThis is test content."
        result = write_file("test/new_file.md", test_content)
        
        assert result == {"success": True}
        
        # Verify file was created
        test_file = vault_path / "test" / "new_file.md"
        assert test_file.exists()
        assert test_file.read_text() == test_content
    
    def test_write_file_creates_directories(self, vault_path):
        """Test that write_file creates parent directories."""
        test_content = "# Deep Test\n\nNested content."
        result = write_file("deep/nested/path/test.md", test_content)
        
        assert result == {"success": True}
        
        # Verify directory structure was created
        test_file = vault_path / "deep" / "nested" / "path" / "test.md"
        assert test_file.exists()
        assert test_file.parent.exists()
    
    def test_write_file_path_traversal(self):
        """Test that path traversal is prevented in write operations."""
        result = write_file("../../../tmp/evil.txt", "evil content")
        
        assert "error" in result
        assert "Invalid input" in result["error"]


class TestJournalTools:
    """Test journal-related tools."""
    
    def test_list_todays_journal_entry(self, mock_mcp_server):
        """Test getting today's journal entry path."""
        # Register tools
        register_journal_tools(mock_mcp_server)
        
        # Test the utility function that would be called by the tool
        from obsidian_mcp.utils import get_today_journal_path
        
        result_path = get_today_journal_path()
        assert result_path.startswith("journal/")
        assert result_path.endswith(".md")
    
    def test_list_journal_entries_by_year_and_month(self, mock_mcp_server, vault_path):
        """Test listing journal entries for a specific month."""
        register_journal_tools(mock_mcp_server)
        
        # Create additional test entries
        test_dir = vault_path / "journal" / "2025" / "01"
        test_dir.mkdir(parents=True, exist_ok=True)
        
        (test_dir / "2025-01-16.md").write_text("# Jan 16\nContent")
        (test_dir / "2025-01-17.md").write_text("# Jan 17\nContent")
        
        # Test the utility function that would be called by the tool
        from obsidian_mcp.utils import list_files_in_directory
        files = list_files_in_directory(test_dir, vault_path)
        
        # Should find multiple journal entries
        assert len(files) >= 2
        assert any(f["name"] == "2025-01-15.md" for f in files)


class TestKnowledgeTools:
    """Test knowledge management tools."""
    
    def test_create_and_list_knowledge_topics(self, mock_mcp_server, vault_path):
        """Test creating and listing knowledge topics."""
        register_knowledge_tools(mock_mcp_server)
        
        # Create test topics
        knowledge_dir = vault_path / "knowledge"
        (knowledge_dir / "test-topic").mkdir(parents=True, exist_ok=True)
        (knowledge_dir / "another-topic").mkdir(parents=True, exist_ok=True)
        
        # Test listing topics
        from obsidian_mcp.utils import list_directories_in_directory
        topics = list_directories_in_directory(knowledge_dir, vault_path)
        
        topic_names = [t["name"] for t in topics]
        assert "test-topic" in topic_names
        assert "another-topic" in topic_names
    
    def test_list_topic_content(self, vault_path):
        """Test listing content within a topic."""
        # Create test topic with content
        topic_dir = vault_path / "knowledge" / "machine-learning"
        topic_dir.mkdir(parents=True, exist_ok=True)
        
        (topic_dir / "neural-networks.md").write_text("# Neural Networks\nContent")
        (topic_dir / "algorithms.md").write_text("# Algorithms\nContent")
        
        from obsidian_mcp.utils import list_files_in_directory
        files = list_files_in_directory(topic_dir, vault_path, recursive=True)
        
        file_names = [f["name"] for f in files]
        assert "neural-networks.md" in file_names
        assert "algorithms.md" in file_names


class TestProjectTools:
    """Test project management tools."""
    
    def test_create_and_list_projects(self, mock_mcp_server, vault_path):
        """Test creating and listing projects."""
        register_projects_tools(mock_mcp_server)
        
        # Create test projects
        projects_dir = vault_path / "projects"
        (projects_dir / "test-project").mkdir(parents=True, exist_ok=True)
        (projects_dir / "another-project").mkdir(parents=True, exist_ok=True)
        
        # Test listing projects
        from obsidian_mcp.utils import list_directories_in_directory
        projects = list_directories_in_directory(projects_dir, vault_path)
        
        project_names = [p["name"] for p in projects]
        assert "test-project" in project_names
        assert "another-project" in project_names
    
    def test_list_project_content(self, vault_path):
        """Test listing content within a project."""
        # Create test project with content
        project_dir = vault_path / "projects" / "website-redesign"
        project_dir.mkdir(parents=True, exist_ok=True)
        
        (project_dir / "requirements.md").write_text("# Requirements\nContent")
        (project_dir / "design.md").write_text("# Design\nContent")
        
        from obsidian_mcp.utils import list_files_in_directory
        files = list_files_in_directory(project_dir, vault_path, recursive=True)
        
        file_names = [f["name"] for f in files]
        assert "requirements.md" in file_names
        assert "design.md" in file_names


class TestIntegration:
    """Integration tests combining multiple operations."""
    
    def test_full_workflow_journal(self, vault_path):
        """Test a complete journal workflow."""
        # 1. Create a new journal entry
        today_path = f"journal/2025/01/2025-01-20.md"
        content = "# January 20, 2025\n\n## Notes\nTest entry"
        
        result = write_file(today_path, content)
        assert result == {"success": True}
        
        # 2. Read it back
        result = read_file(today_path)
        assert "content" in result
        assert "January 20, 2025" in result["content"]
        
        # 3. Verify it appears in directory listing
        from obsidian_mcp.utils import list_files_in_directory
        jan_dir = vault_path / "journal" / "2025" / "01"
        files = list_files_in_directory(jan_dir, vault_path)
        
        assert any(f["name"] == "2025-01-20.md" for f in files)
    
    def test_full_workflow_knowledge(self, vault_path):
        """Test a complete knowledge management workflow."""
        # 1. Create a topic directory
        topic_dir = vault_path / "knowledge" / "testing"
        topic_dir.mkdir(parents=True, exist_ok=True)
        
        # 2. Add content to the topic
        content = "# Testing Knowledge\n\nTesting concepts and practices."
        result = write_file("knowledge/testing/overview.md", content)
        assert result == {"success": True}
        
        # 3. Read the content back
        result = read_file("knowledge/testing/overview.md")
        assert "Testing Knowledge" in result["content"]
        
        # 4. Verify topic listing
        from obsidian_mcp.utils import list_directories_in_directory
        knowledge_dir = vault_path / "knowledge"
        topics = list_directories_in_directory(knowledge_dir, vault_path)
        
        assert any(t["name"] == "testing" for t in topics)