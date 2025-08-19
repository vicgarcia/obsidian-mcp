# Claude Code Project Context

## Project Overview

**Obsidian MCP Server** - A Model Context Protocol (MCP) server that provides Claude Desktop with seamless access to Obsidian vaults. Built using FastMCP Python framework with Docker deployment support.

## Current Status: ✅ PRODUCTION READY

The project is **complete and fully functional** with:
- All 8 MCP tools implemented according to PRD specifications
- Clean architecture with separated concerns (models, utils, business logic)
- Comprehensive test suite (42 tests, all passing)
- Docker deployment ready for Claude Desktop integration
- Timezone-aware date handling for accurate journal entries
- Zero known issues or TODOs

## Key Architecture Decisions

### 1. **Pydantic Models in `models.py`**
- All input validation models moved from `utils.py` to `models.py`
- `utils.py` now contains only helper functions
- Clean separation of concerns

### 2. **Docker-First Deployment**
- Removed docker-compose (unnecessary complexity)
- Simple Dockerfile with minimal dependencies
- User permission handling via `--user` flag in Docker run command
- No README requirement in pyproject.toml (removed for clean builds)

### 3. **Test Structure**
- Focused on end-to-end and core functionality testing
- No coverage reporting (removed as unnecessary overhead)
- Fast execution (~1.2 seconds)
- 42 comprehensive tests covering models, utils, and e2e workflows

### 4. **Timezone Support**
- Timezone-aware datetime handling using `zoneinfo`
- Docker containers default to `America/New_York` timezone
- Configurable via `TZ` environment variable
- Prevents date discrepancies between local and UTC time

### 5. **Removed Features**
- ❌ Templates functionality (templates.py) - explicitly removed per user request
- ❌ Docker Compose - simplified to pure Docker
- ❌ Coverage testing - removed overhead
- ❌ Native installation docs - Docker-only approach

## Project Structure

```
src/obsidian_mcp/
├── __init__.py          # Package initialization
├── server.py           # Main MCP server and general file operations
├── models.py           # Pydantic models for input validation
├── utils.py            # Utility functions and helpers
├── journal.py          # Journal-specific tools
├── knowledge.py        # Knowledge base tools
└── projects.py         # Project management tools

tests/
├── conftest.py         # Test configuration and fixtures
├── test_utils.py       # Unit tests for utility functions  
├── test_models.py      # Tests for Pydantic models
├── test_e2e.py         # End-to-end integration tests
└── fixtures/vault/     # Test data and vault structure
```

## MCP Tools Implemented (8 total)

### General File Operations
- `read_file` - Read file content with security validation
- `write_file` - Write files with automatic directory creation

### Journal Tools
- `list_todays_journal_entry` - Get today's journal path
- `list_journal_entries_by_year_and_month` - List monthly entries

### Knowledge Tools
- `list_knowledge_topics` - List topic directories
- `list_topic_content` - List files in topic (recursive)
- `create_topic` - Create new knowledge topic

### Projects Tools
- `list_projects` - List project directories
- `list_project_content` - List files in project (recursive)  
- `create_project` - Create new project directory

## Deployment

### Build Docker Image
```bash
./build.sh
```

### Claude Desktop Configuration
```json
{
  "mcpServers": {
    "obsidian": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--user", "1000:1000",
        "-v", "/path/to/your/obsidian/vault:/vault",
        "-e", "OBSIDIAN_VAULT_PATH=/vault",
        "-e", "TZ=America/New_York",
        "obsidian-mcp:local"
      ]
    }
  }
}
```

## Testing

```bash
# Quick test run
uv run pytest

# Full test suite
./run_tests.sh
```

## Security Features

- **Path validation**: All file paths validated against vault root
- **Directory traversal prevention**: Using `pathlib.Path.is_relative_to()`
- **Input sanitization**: Comprehensive Pydantic models
- **Read-before-write**: File modifications require reading current content
- **User permissions**: Docker runs as specified user for proper file ownership

## Key Dependencies

- **FastMCP** (>=2.11.3) - MCP server framework
- **Pydantic** (>=2.0.0) - Input validation
- **Python** (>=3.12) - Runtime requirement

## Important Notes

1. **No templates functionality** - This was explicitly removed and should not be re-added
2. **Docker-only deployment** - Native installation documentation removed per user preference
3. **User ID configuration** - Users must set their `--user` flag with correct IDs
4. **File permissions** - Docker handles permissions naturally when run with correct user
5. **Environment variables** - `OBSIDIAN_VAULT_PATH` must point to mounted vault directory
6. **Timezone configuration** - Set `TZ` environment variable to match local timezone for accurate journal dates

## Development Commands

```bash
# Install dependencies
uv sync --extra test

# Run tests
uv run pytest

# Build Docker image
./build.sh

# Test Docker locally
docker run --rm --user "$(id -u):$(id -g)" \
  -v "/path/to/vault:/vault" \
  -e OBSIDIAN_VAULT_PATH=/vault \
  -e TZ=America/New_York \
  obsidian-mcp:local
```

## User Experience

The server is designed for **seamless integration** with Claude Desktop:
1. User builds Docker image with `./build.sh`
2. User adds JSON config to Claude Desktop (with their vault path, user ID, and timezone)
3. Claude Desktop can immediately access and manage Obsidian vault through MCP tools
4. File permissions work correctly due to Docker user mapping
5. Journal entries reflect correct local dates due to timezone configuration

## Context for Future Sessions

- This project is **feature-complete** and **production-ready**
- Focus should be on **maintenance** and **user support** rather than new features
- **Docker deployment** is the primary and recommended approach
- All **architectural decisions** were made deliberately and should be preserved
- The **test suite** is comprehensive and should be maintained