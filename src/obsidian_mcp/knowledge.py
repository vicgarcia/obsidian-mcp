"""Knowledge section tools for the Obsidian MCP server."""

from typing import Dict, Any, List

from pydantic import ValidationError

from .utils import (
    get_vault_base,
    create_error_response,
    create_success_response,
    list_files_in_directory,
    list_directories_in_directory
)
from .models import TopicInput



def register_knowledge_tools(mcp):
    """Register knowledge-related tools with the MCP server."""
    
    @mcp.tool()
    def list_knowledge_topics() -> List[Dict[str, str]]:
        """
        List all knowledge topics (subdirectories in the knowledge directory).
        
        Returns:
            List of topic directories with metadata
        """
        try:
            vault_base = get_vault_base()
            knowledge_dir = vault_base / "knowledge"
            
            # Get all subdirectories in the knowledge directory
            topics = list_directories_in_directory(knowledge_dir, vault_base)
            
            return topics
            
        except ValueError as e:
            return [create_error_response(str(e))]
        except Exception as e:
            return [create_error_response(f"Unexpected error listing knowledge topics: {e}")]
    
    
    @mcp.tool()
    def list_topic_content(topic: str) -> List[Dict[str, str]]:
        """
        List all files and directories within a knowledge topic.
        
        Args:
            topic: Name of the topic directory
            
        Returns:
            List of files and directories with metadata
        """
        try:
            # Validate input
            validated_input = TopicInput(topic=topic)
            
            vault_base = get_vault_base()
            topic_dir = vault_base / "knowledge" / validated_input.topic
            
            # Check if topic directory exists
            if not topic_dir.exists():
                return [create_error_response(f"Topic not found: {validated_input.topic}")]
            
            if not topic_dir.is_dir():
                return [create_error_response(f"Topic is not a directory: {validated_input.topic}")]
            
            # Get all files recursively in the topic directory
            files = list_files_in_directory(topic_dir, vault_base, recursive=True)
            
            return files
            
        except ValidationError as e:
            return [create_error_response(f"Invalid input: {e}")]
        except ValueError as e:
            return [create_error_response(str(e))]
        except Exception as e:
            return [create_error_response(f"Unexpected error listing topic content: {e}")]
    
    
    @mcp.tool()
    def create_topic(topic: str) -> Dict[str, Any]:
        """
        Create a new knowledge topic directory.
        
        Args:
            topic: Name of the topic directory to create
            
        Returns:
            Success indicator or error message
        """
        try:
            # Validate input
            validated_input = TopicInput(topic=topic)
            
            vault_base = get_vault_base()
            topic_dir = vault_base / "knowledge" / validated_input.topic
            
            # Create the directory (parents=True creates knowledge dir if it doesn't exist)
            topic_dir.mkdir(parents=True, exist_ok=True)
            
            return create_success_response()
            
        except ValidationError as e:
            return create_error_response(f"Invalid input: {e}")
        except ValueError as e:
            return create_error_response(str(e))
        except Exception as e:
            return create_error_response(f"Unexpected error creating topic: {e}")