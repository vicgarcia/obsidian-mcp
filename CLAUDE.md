# Claude Code Session Documentation

## Project Overview
Obsidian MCP Server - A modular Python MCP server for accessing an Obsidian vault in Claude Desktop. Built with MCP, implements 10 core tools for journal entries, projects, and wiki articles. Intentionally minimal to keep context usage low and let Claude handle interpretation.

Installable via `uv tool install`.

## Project Structure
```
obsidian-mcp/
├── src/
│   └── obsidian_mcp/
│       ├── __init__.py       # package init, version, exports
│       ├── server.py         # FastMCP server + 10 tools
│       ├── vault_client.py   # vault operations (context manager)
│       └── schema.py         # Pydantic validation models
├── tests/
│   ├── conftest.py           # pytest fixtures
│   ├── test_schema.py        # validation model tests
│   ├── test_vault_client.py  # vault client tests
│   ├── test_tools.py         # MCP tool tests
│   └── test_integration.py   # integration tests
├── pyproject.toml            # package metadata and dependencies
├── Dockerfile                # docker deployment
├── README.md                 # user-facing documentation
└── CLAUDE.md                 # this file
```

## External Documentation

### Key References
- **MCP Documentation**: https://modelcontextprotocol.io - Model Context Protocol specification
- **Obsidian**: https://obsidian.md - The note-taking app this server interfaces with

## Quick Reference

### Development Commands
```bash
uv tool install --editable .              # install in dev mode
obsidian-mcp --vault /path/to/vault       # run
docker build -t obsidian-mcp:local .      # build docker image
uv run pytest tests/ -v                   # run tests
```

### Installation
```bash
uv tool install git+https://github.com/vicgarcia/obsidian-mcp
```

### Environment Variables
- `OBSIDIAN_VAULT_PATH`: Path to vault (default: /vault, or use --vault flag)
- `TZ`: Timezone for journal dates (e.g., America/New_York)
- `LOG_LEVEL`: Optional. DEBUG or INFO (default: INFO)

## Tools Overview
Ten core MCP tools (see README.md for full documentation):
- `read_file` / `write_file` - General file operations
- `get_current_date` - Current date in multiple formats
- `list_todays_journal_entry` - Get today's journal path
- `start_daily_notes_session` - Interactive daily notes workflow
- `list_journal_entries_by_year_and_month` - List entries for a month
- `list_projects` / `list_project_content` / `create_project` - Project management
- `list_wiki` - List wiki articles

## Implementation Notes

### Architecture Decisions
- **Modular package structure**: Separation of concerns into distinct modules
- **VaultClient context manager**: Clean resource management for vault operations
- **Schema module**: Centralized Pydantic validation models
- **MCP FastMCP**: Used for MCP server framework (simpler than raw MCP protocol)
- **STDIO Transport**: Default for Claude Desktop compatibility
- **Dual deployment**: `uv tool install` for native, Docker for isolation

### Module Organization

#### schema.py (Data Models)
- `YearMonthInput` - Year/month validation
- `FilePathInput` - File path validation with traversal protection
- `FileWriteInput` - File write input validation
- `ProjectInput` - Project name validation
- `create_error_response()` / `create_success_response()` - Response helpers

#### vault_client.py (Vault Operations)
- `VaultClient` - Context manager for all vault operations
- `VaultError` - Custom exception for vault errors
- File operations: `read_file()`, `write_file()`, `file_exists()`
- Directory operations: `list_files()`, `list_directories()`, `create_directory()`
- Journal operations: `get_journal_path()`, `list_journal_entries()`
- Project operations: `list_projects()`, `list_project_content()`, `create_project()`
- Wiki operations: `list_wiki()`

#### server.py (MCP Server)
- FastMCP server initialization
- 10 `@mcp.tool()` definitions
- Module-level client singleton
- Entry point `run()` function

### Code Quality Features
- Type hints throughout
- Consistent error handling patterns: `{"error": "message", "success": False}`
- Structured logging with configurable levels (all lowercase except proper names)
- Path security validation (no traversal attacks)
- Context manager pattern for resource management

### Entry Point Flow
```python
run()
  → logging.basicConfig(...)
  → parse_args()            # --vault or OBSIDIAN_VAULT_PATH
  → validate vault exists
  → _client = VaultClient(...)  # Initialize singleton
  → mcp.run()               # Start FastMCP server
```

## Design Decisions

### What We Built
- **Modular architecture**: 3 core modules with clear responsibilities
- **10 tools**: Covering three workflows (files/journal, projects, wiki)
- **Strict filesystem structure**: `journal/YYYY/MM/`, `projects/`, `wiki/`
- **Dual deployment**: uv tool install + Docker
- **Path validation**: Security-first file operations
- **Comprehensive test suite**: Tests generated on the fly

### What We Didn't Build
- No templates (just create files directly)
- No tag support (filesystem organization is enough)
- No complex queries (let Claude interpret)
- No file deletion/moving (use read/write instead)
- No metadata parsing (filenames describe content)

## Code Conventions

### Naming & Style
- Comments in lowercase (except proper names/symbols)
- Docstrings use triple single quotes: `''' like this '''`
- Lowercase log messages except proper names
- Consistent error responses: `{"error": "message", "success": False}`
- Files end with blank line
- Single quotes for strings

### Testing
- Tests organized by module (test_schema.py, test_vault_client.py, test_tools.py)
- Integration tests in test_integration.py
- Test data generated on the fly using pytest tmp_path
