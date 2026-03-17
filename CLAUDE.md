# Claude Code Session Documentation

## Project Overview
Obsidian MCP Server - A minimal Python MCP server for accessing an Obsidian vault in Claude Desktop. Built with MCP, implements 12 core tools for journal entries, projects, wiki articles, and agent prompts. Intentionally minimal to keep context usage low and let Claude handle interpretation.

Single-file module installable via `uv tool install`.

## Project Structure
```
obsidian-mcp/
├── obsidian_mcp.py       # single-file module (all logic + MCP server)
├── obsidian_mcp_test.py  # tests
├── tests/fixtures/vault/ # test vault structure
├── pyproject.toml        # package metadata and dependencies
├── Dockerfile            # docker deployment
├── README.md             # user-facing documentation
└── CLAUDE.md             # this file
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
uv run pytest                              # run tests
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
Twelve core MCP tools (see README.md for full documentation):
- `read_file` / `write_file` - General file operations
- `get_current_date` - Current date in multiple formats
- `list_todays_journal_entry` - Get today's journal path
- `start_daily_notes_session` - Interactive daily notes workflow
- `list_journal_entries_by_year_and_month` - List entries for a month
- `list_projects` / `list_project_content` / `create_project` - Project management
- `list_wiki` - List wiki articles
- `list_prompts` / `read_prompt` - Access agent prompts

## Implementation Notes

### Architecture Decisions
- **Single-file module**: All logic in `obsidian_mcp.py`, installed via pyproject.toml
- **MCP FastMCP**: Used for MCP server framework (simpler than raw MCP protocol)
- **Pydantic**: Input validation for all file paths and parameters
- **STDIO Transport**: Default for Claude Desktop compatibility
- **Dual deployment**: `uv tool install` for native, Docker for isolation

### Code Quality Features
- Type hints throughout
- Consistent error handling patterns: `{"error": "message", "success": False}`
- Structured logging with configurable levels (all lowercase except proper names)
- Path security validation (no traversal attacks)

### File Organization (within obsidian_mcp.py)
- **Arg parsing** — `parse_args()`, `_HELP` constant
- **Pydantic models** — Input validation classes
- **Utility functions** — `get_vault_base()`, `validate_vault_path()`, helpers
- **MCP server** — `mcp = FastMCP(...)`, 12 `@mcp.tool()` definitions
- **Entry point** — `run()`, `if __name__ == '__main__': run()`

### Entry Point Flow
```python
run()
  → logging.basicConfig(...)
  → parse_args()            # --vault or OBSIDIAN_VAULT_PATH
  → set_vault_path(...)     # Configure module-level path
  → validate vault exists
  → mcp.run()               # Start FastMCP server
```

## Design Decisions

### What We Built
- **Minimal tool set**: 12 operations covering four workflows
- **Strict filesystem structure**: `journal/YYYY/MM/`, `projects/`, `wiki/`, `prompts/`
- **Dual deployment**: uv tool install + Docker
- **Path validation**: Security-first file operations

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
