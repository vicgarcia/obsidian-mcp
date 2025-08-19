"""Projects section tools for the Obsidian MCP server."""

from typing import Dict, Any, List

from pydantic import ValidationError

from .utils import (
    get_vault_base,
    create_error_response,
    create_success_response,
    list_files_in_directory,
    list_directories_in_directory
)
from .models import ProjectInput




def register_projects_tools(mcp):
    """Register project-related tools with the MCP server."""
    
    @mcp.tool()
    def list_projects() -> List[Dict[str, str]]:
        """
        List all projects (subdirectories in the projects directory).
        
        Returns:
            List of project directories with metadata
        """
        try:
            vault_base = get_vault_base()
            projects_dir = vault_base / "projects"
            
            # Get all subdirectories in the projects directory
            projects = list_directories_in_directory(projects_dir, vault_base)
            
            return projects
            
        except ValueError as e:
            return [create_error_response(str(e))]
        except Exception as e:
            return [create_error_response(f"Unexpected error listing projects: {e}")]
    
    
    @mcp.tool()
    def list_project_content(project: str) -> List[Dict[str, str]]:
        """
        List all files and directories within a project.
        
        Args:
            project: Name of the project directory
            
        Returns:
            List of files and directories with metadata
        """
        try:
            # Validate input
            validated_input = ProjectInput(project=project)
            
            vault_base = get_vault_base()
            project_dir = vault_base / "projects" / validated_input.project
            
            # Check if project directory exists
            if not project_dir.exists():
                return [create_error_response(f"Project not found: {validated_input.project}")]
            
            if not project_dir.is_dir():
                return [create_error_response(f"Project is not a directory: {validated_input.project}")]
            
            # Get all files recursively in the project directory
            files = list_files_in_directory(project_dir, vault_base, recursive=True)
            
            return files
            
        except ValidationError as e:
            return [create_error_response(f"Invalid input: {e}")]
        except ValueError as e:
            return [create_error_response(str(e))]
        except Exception as e:
            return [create_error_response(f"Unexpected error listing project content: {e}")]
    
    
    @mcp.tool()
    def create_project(project: str) -> Dict[str, Any]:
        """
        Create a new project directory.
        
        Args:
            project: Name of the project directory to create
            
        Returns:
            Success indicator or error message
        """
        try:
            # Validate input
            validated_input = ProjectInput(project=project)
            
            vault_base = get_vault_base()
            project_dir = vault_base / "projects" / validated_input.project
            
            # Create the directory (parents=True creates projects dir if it doesn't exist)
            project_dir.mkdir(parents=True, exist_ok=True)
            
            return create_success_response()
            
        except ValidationError as e:
            return create_error_response(f"Invalid input: {e}")
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response(f"Unexpected error creating project: {e}")