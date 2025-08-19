"""Main MCP server implementation for Obsidian vault access."""

import sys
from typing import Dict, Any

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from .utils import (
    get_vault_base,
    validate_vault_path,
    create_error_response,
    create_success_response
)
from .models import FilePathInput, FileWriteInput
from .journal import register_journal_tools
from .knowledge import register_knowledge_tools
from .projects import register_projects_tools


# Initialize the MCP server
mcp = FastMCP("Obsidian MCP Server")


@mcp.tool()
def read_file(file_path: str) -> Dict[str, Any]:
    """
    Read file content from the Obsidian vault.
    
    Args:
        file_path: Vault-relative path to the file
        
    Returns:
        Dictionary with file content or error message
    """
    try:
        # Validate input
        validated_input = FilePathInput(file_path=file_path)
        
        # Validate and resolve vault path
        vault_path = validate_vault_path(validated_input.file_path)
        
        # Check if file exists
        if not vault_path.exists():
            return create_error_response(f"File not found: {validated_input.file_path}")
        
        # Check if it's actually a file
        if not vault_path.is_file():
            return create_error_response(f"Path is not a file: {validated_input.file_path}")
        
        # Read file content
        try:
            # Try to read as text file
            content = vault_path.read_text(encoding='utf-8')
            return {"content": content}
        except UnicodeDecodeError:
            # If it's a binary file, return error
            return create_error_response(f"Cannot read binary file: {validated_input.file_path}")
        
    except ValidationError as e:
        return create_error_response(f"Invalid input: {e}")
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response(f"Unexpected error reading file: {e}")


@mcp.tool()
def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """
    Write content to a file in the Obsidian vault.
    
    Args:
        file_path: Vault-relative path to the file
        content: Content to write to the file
        
    Returns:
        Dictionary with success indicator or error message
    """
    try:
        # Validate input
        validated_input = FileWriteInput(file_path=file_path, content=content)
        
        # Validate and resolve vault path
        vault_path = validate_vault_path(validated_input.file_path)
        
        # Create parent directories if they don't exist
        vault_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file content
        vault_path.write_text(validated_input.content, encoding='utf-8')
        
        return create_success_response()
        
    except ValidationError as e:
        return create_error_response(f"Invalid input: {e}")
    except ValueError as e:
        return create_error_response(str(e))
    except Exception as e:
        return create_error_response(f"Unexpected error writing file: {e}")


def main():
    """Main entry point for the MCP server."""
    try:
        # Validate that vault path is configured
        vault_base = get_vault_base()
        
        # Ensure vault directory exists
        if not vault_base.exists():
            print(f"Error: Vault directory does not exist: {vault_base}", file=sys.stderr)
            sys.exit(1)
        
        if not vault_base.is_dir():
            print(f"Error: Vault path is not a directory: {vault_base}", file=sys.stderr)
            sys.exit(1)
        
        # Register tools from other modules
        register_journal_tools(mcp)
        register_knowledge_tools(mcp)
        register_projects_tools(mcp)
        
        # Run the server
        mcp.run()
        
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()