# Product Requirements Document: Obsidian MCP Server

## Project Overview

The Obsidian MCP Server is a Model Context Protocol (MCP) server that provides Claude Desktop with seamless access to Obsidian, a popular knowledge management and note-taking application. This server acts as a bridge between Claude's AI capabilities and Obsidian's rich note ecosystem, enabling intelligent interactions with personal knowledge bases.

## Purpose

This MCP server enables Claude to:
- Read and analyze notes from Obsidian vaults
- Create and update notes with AI-generated content
- Navigate and understand the structure of knowledge graphs
- Perform intelligent operations on linked notes and concepts
- Maintain consistency with Obsidian's markdown format and conventions

## Target Users

- Knowledge workers who use Obsidian for personal knowledge management
- Researchers and writers who want AI assistance with their note collections
- Claude Desktop users seeking to integrate their Obsidian workflow with AI capabilities

## Key Benefits

- **Seamless Integration**: Direct access to Obsidian vaults from Claude Desktop
- **Opinionated Design**: Follows Obsidian best practices and conventions
- **Intelligent Operations**: Leverages Claude's understanding of context and relationships
- **Privacy-First**: Operates locally without sending data to external services

## Technical Architecture

The server implements the Model Context Protocol specification using the FastMCP Python framework, providing:
- Resource discovery and access to Obsidian notes
- Tool interfaces for note creation and modification
- Proper handling of Obsidian's markdown extensions and linking syntax

### Implementation Framework

**FastMCP Server**
- Built using Python FastMCP library for MCP protocol implementation
- Uses STDIO transport for Claude Desktop integration
- Implements MCP tools pattern for file operations and directory listing
- Leverages Pydantic models for input validation and type safety
- Includes proper error handling and path validation for security

**MCP Primitive Mapping**
- **Tools**: File operations (`read_file`, `write_file`) and all listing operations
- **Resources**: Not used (tools provide sufficient functionality)
- **Prompts**: Not used (focusing on data access functionality)

**Server Structure**
```python
import os
from mcp.server.fastmcp import FastMCP, Context
from pathlib import Path
from pydantic import BaseModel, field_validator
from typing import List, Optional

# Initialize vault base path from environment
VAULT_BASE = Path(os.getenv('OBSIDIAN_VAULT_PATH')).resolve()

mcp = FastMCP("Obsidian MCP Server")

@mcp.tool()
def read_file(file_path: str) -> dict:
    """Read file content with pathlib validation"""
    vault_path = VAULT_BASE / Path(file_path)
    if not vault_path.is_relative_to(VAULT_BASE):
        raise ValueError("Invalid path")
    # Implementation with pathlib operations

@mcp.tool()
def write_file(file_path: str, content: str) -> dict:
    """Write file content using pathlib"""
    vault_path = VAULT_BASE / Path(file_path)
    vault_path.parent.mkdir(parents=True, exist_ok=True)
    # Implementation with pathlib methods
```

### Content Modification Safety Pattern

**Read-Then-Write Requirement**
- All content modification operations must be preceded by a read operation
- AI agents must retrieve current file content before making any changes
- This ensures awareness of existing content and prevents accidental overwrites
- Write operations replace entire file content, giving maximum flexibility for modifications
- No restrictions on where or how changes can be made within files

### General File Operations

**File Reading**
- Tool: `read_file`
- Parameters: `file_path` (vault-relative path)
- Returns: File content and metadata
- Behavior: Reads any file type, handles text/binary detection automatically
- Supports markdown, text, PDF, images, and other file formats

**File Writing**
- Tool: `write_file`
- Parameters: `file_path` (vault-relative path), `content` (file content)
- Returns: Confirmation and file metadata
- Behavior: Creates or overwrites files, automatically creates directories as needed
- Safety: Must be preceded by a read operation for existing files
- Uses vault-relative paths for all operations

### Configuration and Deployment

**Server Configuration**
- Vault path configuration via environment variable `OBSIDIAN_VAULT_PATH` (required)
- All file operations use Python's `pathlib.Path` library for cross-platform compatibility
- Vault base path resolved using `Path(os.getenv('OBSIDIAN_VAULT_PATH')).resolve()`
- All vault-relative paths converted to absolute paths via `vault_base / relative_path`
- Server runs via STDIO transport for Claude Desktop integration

**Deployment and Dependencies**
- Built as Docker container for consistent deployment
- Dependencies managed via `pyproject.toml`, development with `uv`, container installs with `pip`
- Primary dependencies: `mcp` (FastMCP framework), `pydantic` (validation)
- Entry point defined as `obsidian-mcp` in `pyproject.toml` for server execution
- Container exposes STDIO transport for MCP communication
- Volume mount required for vault access: `-v /path/to/vault:/vault`
- Environment variable: `OBSIDIAN_VAULT_PATH=/vault`

**Tool Response Formats**

*File Listing Tools* (return list of file objects):
```json
[
  {"path": "journal/2025/01/2025-01-15.md", "name": "2025-01-15.md"},
  {"path": "knowledge/cooking/recipes.md", "name": "recipes.md"}
]
```

*Directory Listing Tools* (return list of directory objects):
```json
[
  {"path": "knowledge/machine-learning", "name": "machine-learning"},
  {"path": "projects/website-redesign", "name": "website-redesign"}
]
```

*File Reading Tool* (return content as string, text files only):
```json
{"content": "# Journal Entry\n\nToday I learned..."}
```

*File Writing Tool* (return success indicator):
```json
{"success": true}
```

*Error Responses* (all tools):
```json
{"error": "File not found: journal/2025/01/2025-01-30.md"}
```

**Error Handling Strategy**
- File not found errors return structured error responses with descriptive messages
- Path validation prevents directory traversal attacks
- Invalid date formats in journal operations return validation errors
- All tools return standardized error format with string message

**Input Validation Models**
```python
class JournalDateInput(BaseModel):
    date: str
    
    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        # Validate YYYY-MM-DD format
        return v

class YearMonthInput(BaseModel):
    year: str
    month: str
    
    @field_validator("year", "month")
    @classmethod
    def validate_date_parts(cls, v: str) -> str:
        # Validate year/month formats
        return v
```

**File System Security**
- All file paths validated against vault root directory using `pathlib.Path`
- Path traversal prevention using `Path.resolve()` and `Path.is_relative_to()` checks
- Vault-relative paths joined using `vault_base / Path(relative_path)` for safety
- File reading limited to text files only (binary support planned for future)
- Directory creation restricted to vault subdirectories only
- All path operations use `pathlib.Path` methods for consistency and security
- No file size limits enforced (may be added in future revisions)
- Single-user access assumed (no concurrent access protection)

## MCP Tools Inventory

| Tool Name | Section | Parameters | Returns | Description |
|-----------|---------|------------|---------|-------------|
| `read_file` | General | `file_path: str` | `{"content": "..."}` | Read text file content as string |
| `write_file` | General | `file_path: str`, `content: str` | `{"success": true}` | Write/create file with content |
| `list_todays_journal_entry` | Journal | None | `{"path": "journal/...", "name": "..."}` | Get today's journal entry path |
| `list_journal_entries_by_year_and_month` | Journal | `year: str`, `month: str` | `[{"path": "...", "name": "..."}]` | List journal entries for month |
| `list_knowledge_topics` | Knowledge | None | `[{"path": "knowledge/...", "name": "..."}]` | List all knowledge topics |
| `list_topic_content` | Knowledge | `topic: str` | `[{"path": "...", "name": "..."}]` | List files in knowledge topic |
| `create_topic` | Knowledge | `topic: str` | `{"success": true}` | Create empty knowledge topic directory |
| `list_projects` | Projects | None | `[{"path": "projects/...", "name": "..."}]` | List all projects |
| `list_project_content` | Projects | `project: str` | `[{"path": "...", "name": "..."}]` | List files in project |
| `create_project` | Projects | `project: str` | `{"success": true}` | Create empty project directory |

## Functional Sections

### Journal

The Journal section provides structured daily note-taking capabilities following a hierarchical date-based organization system.

#### Directory Structure
```
journal/
├── 2025/
│   ├── 01/
│   │   ├── 2025-01-01.md
│   │   ├── 2025-01-02.md
│   │   └── ...
│   ├── 02/
│   └── ...
├── 2024/
│   ├── 01/
│   ├── 02/
│   └── ...
└── ...
```

#### Feature Requirements

**Today's Journal Entry**
- Tool: `list_todays_journal_entry`
- Parameters: None (uses current date)
- Returns: Vault-relative path for today's journal entry
- Behavior: Returns the expected path for today's journal entry (format: `journal/YYYY/MM/YYYY-MM-DD.md`)
- Use case: Allows agents to quickly access today's journal without listing entire months
- Use with `read_file` to check if entry exists, or `write_file` to create/update

**Journal Entry Listing**
- Tool: `list_journal_entries_by_year_and_month`
- Parameters: `year` (YYYY format), `month` (MM format, required)
- Returns: List of journal entries with metadata and vault-relative paths
- Behavior: Lists all entries for the specified year/month combination
- Response includes file metadata (name, path, size, modified date) for each entry
- Use `read_file` with returned paths to access content

**Data Requirements**
- All journal entries are stored as standard markdown files
- Filenames follow strict `YYYY-MM-DD.md` format
- Directory structure uses zero-padded months (01, 02, ..., 12)
- All tools use vault-relative paths consistently
- Journal entry path format: `journal/YYYY/MM/YYYY-MM-DD.md`
- Use general `read_file` and `write_file` tools to access/modify content
- `write_file` automatically creates directory structure as needed

### Knowledge

The Knowledge section provides topic-based organization for research, notes, and reference materials. Each topic maintains its own directory with associated files and subdirectories.

#### Directory Structure
```
knowledge/
├── machine-learning/
│   ├── neural-networks.md
│   ├── algorithms.md
│   ├── papers/
│   │   ├── attention-is-all-you-need.pdf
│   │   └── transformer-survey.pdf
│   └── datasets/
├── philosophy/
│   ├── ethics.md
│   ├── metaphysics.md
│   └── references.md
├── cooking/
│   ├── recipes.md
│   ├── techniques.md
│   └── meal-plans/
└── ...
```

#### Feature Requirements

**Topic Discovery**
- Tool: `list_knowledge_topics`
- Parameters: None
- Returns: List of all topic directories with vault-relative paths
- Behavior: Lists all subdirectories within the knowledge directory
- Response format: Array of topic names and their vault-relative paths

**Topic Content Listing**
- Tool: `list_topic_content`
- Parameters: `topic` (topic directory name)
- Returns: Complete directory tree for the specified topic
- Behavior: Recursively lists all files and directories within a topic
- Error: Returns error if topic does not exist
- Response includes file metadata (name, path, size, type, modified date) and vault-relative paths
- Use `read_file` with returned paths to access content

**Topic Creation**
- Tool: `create_topic`
- Parameters: `topic` (topic directory name)
- Returns: Success indicator (`{"success": true}` regardless of whether directory already exists)
- Behavior: Creates empty directory in knowledge section
- Creates directory structure: `knowledge/{topic}/`
- Best practice: Use alphanumeric characters, spaces, hyphens, underscores for topic names


**Data Requirements**
- Topics are represented as subdirectories within the knowledge directory
- Each topic can contain markdown files, PDFs, images, and nested directories
- All operations use vault-relative paths consistently
- Listing tools return metadata only; use `read_file`/`write_file` to access content
- Support for various file formats while maintaining focus on markdown content
- Preserve existing directory structures and file organization

### Projects

The Projects section provides project-based organization for managing active work, documentation, and resources. Each project maintains its own directory with associated files and subdirectories.

#### Directory Structure
```
projects/
├── website-redesign/
│   ├── requirements.md
│   ├── design-mockups.md
│   ├── assets/
│   │   ├── wireframes.pdf
│   │   └── brand-guidelines.pdf
│   └── meeting-notes/
├── mobile-app/
│   ├── user-stories.md
│   ├── technical-spec.md
│   ├── research/
│   └── prototypes/
├── data-migration/
│   ├── plan.md
│   ├── scripts/
│   └── testing/
└── ...
```

#### Feature Requirements

**Project Discovery**
- Tool: `list_projects`
- Parameters: None
- Returns: List of all project directories with vault-relative paths
- Behavior: Lists all subdirectories within the projects directory
- Response format: Array of project names and their vault-relative paths

**Project Content Listing**
- Tool: `list_project_content`
- Parameters: `project` (project directory name)
- Returns: Complete directory tree for the specified project
- Behavior: Recursively lists all files and directories within a project
- Error: Returns error if project does not exist
- Response includes file metadata (name, path, size, type, modified date) and vault-relative paths
- Use `read_file` with returned paths to access content

**Project Creation**
- Tool: `create_project`
- Parameters: `project` (project directory name)
- Returns: Success indicator (`{"success": true}` regardless of whether directory already exists)
- Behavior: Creates empty directory in projects section
- Creates directory structure: `projects/{project}/`
- Best practice: Use alphanumeric characters, spaces, hyphens, underscores for project names

**Data Requirements**
- Projects are represented as subdirectories within the projects directory
- Each project can contain markdown files, PDFs, images, and nested directories
- All operations use vault-relative paths consistently
- Listing tools return metadata only; use `read_file`/`write_file` to access content
- Support for various file formats while maintaining focus on markdown content
- Preserve existing directory structures and file organization

