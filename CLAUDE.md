# Claude Code Project Context

## Project Overview

This is an MCP server for Obsidian vault management. It's intentionally minimal - built to handle journal entries, project tracking, and knowledge management without the complexity of full-featured Obsidian tools.

The server provides Claude Desktop with access to:
- Journal entries organized in a year/month filesystem structure (journal/YYYY/MM/)
- Project directories for organizing work (projects/)
- Knowledge guides for comprehensive topic documentation (knowledge/)
- General file read/write operations across the vault

## Current Status

Production ready. 8 tools implemented, 45 tests passing, Docker deployment configured.

This is feature-complete by design. The goal was simplicity, not comprehensiveness.

## Design Philosophy

### Scope: Journal, Projects, and Knowledge

Most Obsidian MCP servers try to expose everything - tags, templates, complex queries, graph analysis, etc. That creates complexity and maintenance overhead.

This server focuses on three core workflows:
1. **Journal entries**: Daily notes with strict YYYY/MM/DD filesystem hierarchy
2. **Project tracking**: Simple directory-based organization for ongoing work
3. **Knowledge guides**: Flat directory of comprehensive topic documentation

No templates, no knowledge graphs, no tag systems. Just files organized in predictable directories.

### Filesystem Organization

**Journal entries**:
```
journal/YYYY/MM/YYYY-MM-DD.md
```
Month is always two digits with leading zero (01-12, not "10 - October").
This structure is rigid by design - keeps things predictable and makes date-based queries straightforward.

**Projects**:
```
projects/project-name/
```
Each project is a subdirectory. Naming is flexible but must avoid filesystem special characters.
No nested project hierarchies - keep it flat.

**Knowledge guides**:
```
knowledge/topic-name.md
```
Flat structure - all guides live directly in knowledge/ with no subdirectories. Use descriptive filenames that clearly indicate content (e.g., `python-asyncio.md`, `docker-networking.md`, `git-workflows.md`). No metadata, no frontmatter parsing - the filename is the documentation.

### Simplicity Over Features

Every omitted feature is a decision to keep the codebase maintainable:
- No templates (just create files directly)
- No tag support (filesystem organization is enough)
- No complex queries (just list and read)
- No file deletion/moving (use read/write instead)
- No subdirectories in knowledge (flat structure only)
- No metadata parsing (filenames describe content)

Each omitted feature means less code to maintain, fewer edge cases, and faster execution.

## Architecture

### Code Organization

```
src/obsidian_mcp/
├── server.py    # all MCP tools live here
├── models.py    # Pydantic input validation
└── utils.py     # helper functions

tests/
├── conftest.py      # pytest fixtures
├── test_e2e.py      # end-to-end tests
├── test_models.py   # validation tests
└── test_utils.py    # utility tests
```

All MCP tools are in server.py. No need to split into separate modules for such a small tool count.

### Key Decisions

**Pydantic for validation**: Explicit input models catch bad data early. All path inputs, date formats, and file operations go through validation.

**Docker-first deployment**: Simpler than managing Python environments. User permissions map cleanly through Docker's --user flag.

**Timezone awareness**: Journal entries need to respect local time, not UTC. The TZ environment variable handles this.

**No abstraction layers**: Direct path manipulation with pathlib. No ORMs, no query builders, just file operations.

**Logging**: Comprehensive logging throughout using Python's logging module. LOG_LEVEL environment variable (debug/info) controls verbosity. All exceptions logged with full stack traces. All log messages use lowercase except proper names.

## MCP Tools (8 total)

**General file operations**:
- `read_file(file_path)` - read any file in vault
- `write_file(file_path, content)` - write to any file in vault

**Journal operations**:
- `list_todays_journal_entry()` - get path for today in format journal/YYYY/MM/YYYY-MM-DD.md
- `list_journal_entries_by_year_and_month(year, month)` - list entries for specific YYYY/MM

**Project operations**:
- `list_projects()` - list all project directories
- `list_project_content(project)` - list files within a project
- `create_project(project)` - create new project directory

**Knowledge operations**:
- `list_knowledge_guides()` - list all knowledge guides (markdown files only, alphabetically sorted)

No delete/move operations. Read and write handle file modifications.

## Code Style

Non-negotiable conventions:
- Comments in lowercase (except proper names/symbols)
- Docstrings use triple single quotes: `''' like this '''`
- Single-line docstrings have spaces: `''' text '''`
- Files end with blank line
- No file-level docstrings (removed for simplicity)
- Log messages in lowercase (except proper names like YYYY, TZ, etc.)

## Deployment

Docker only. No native installation docs because Docker handles dependencies and permissions cleanly.

Build:
```bash
./build.sh
```

Configure Claude Desktop:
```json
{
  "mcpServers": {
    "obsidian": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--user", "1000:1000",
        "-v", "/path/to/vault:/vault",
        "-e", "OBSIDIAN_VAULT_PATH=/vault",
        "-e", "TZ=America/New_York",
        "-e", "LOG_LEVEL=info",
        "obsidian-mcp:local"
      ]
    }
  }
}
```

User must set:
- Their actual user:group IDs (from `id` command)
- Absolute vault path
- Their timezone
- Optional: LOG_LEVEL (debug for verbose logging, info for normal)

## Security

**Path validation**: All file paths validated against vault root using `pathlib.Path.is_relative_to()`. No traversal attacks.

**Input sanitization**: Pydantic models validate formats before any file operations.

**Principle of least privilege**: Docker runs as specified user, not root. File permissions stay correct.

## Testing

45 tests covering:
- Input validation (models) - 14 tests
- Path operations (utils) - 11 tests
- File operations (e2e) - 6 tests
- Journal tools (e2e) - 2 tests
- Project tools (e2e) - 5 tests
- Knowledge tools (e2e) - 5 tests
- Integration workflows (e2e) - 2 tests

Fast execution (< 1 second). No coverage reporting because it's overhead without value for this codebase size.

Run:
```bash
uv run pytest
```

## Dependencies

Minimal:
- FastMCP (>= 2.11.3) - MCP framework
- Pydantic (>= 2.0.0) - validation
- Python 3.12+ - runtime

No database, no web framework, no query engines.

## What Was Removed (Then Re-added)

**Removed in stripped-down version**:
- Templates system (templates.py) - stayed removed
- Knowledge base tools (knowledge.py) - **re-added by user request (simplified)**
- Project management (projects.py) - **re-added by user request**
- Docker Compose setup - stayed removed
- Coverage testing - stayed removed
- Native installation paths - stayed removed

**Project management restored**: User explicitly requested projects functionality be restored. Unlike the first version with separate files (journal.py, knowledge.py, projects.py), all tools now live in server.py for simplicity.

**Knowledge management added**: User requested knowledge guide support. Unlike the original complex knowledge base with templates and metadata, this version is minimal - just list markdown files in knowledge/. No templates, no frontmatter, no complex queries. Filename describes content.

## Context for Future Sessions

- This is feature-complete by design
- Focus is maintenance and bug fixes, not new features
- Don't add removed functionality (templates) without explicit request
- Architecture decisions were intentional, not accidental
- Simplicity is the goal, not comprehensiveness

Current scope: journal entries + project tracking + knowledge guides. No templates, no complex queries, no metadata parsing.

## Development Workflow

1. Changes go through tests first
2. Code style rules are non-negotiable
3. Keep dependencies minimal
4. Docker is the deployment path
5. Don't break the 8-tool interface

## Entry Points

- **Console script**: `obsidian-mcp` (configured in pyproject.toml)
- **Main function**: `obsidian_mcp.server.run()`
- **Package import**: `from obsidian_mcp import run`
- **No `__main__` blocks**: Entry point configured via pyproject.toml only
- **No `__all__` exports**: Keep imports simple

## Recent Changes

### Previous Session

**Projects functionality restored**: Re-added from git history (commit e4e1b44) but integrated into server.py instead of separate projects.py file.

**Logging added**: Comprehensive logging throughout codebase:
- `server.py` and `utils.py` both have logger instances
- `run()` function configures logging.basicConfig with LOG_LEVEL env var
- All tool functions log entry, success, warnings, and errors
- All exceptions logged with full stack traces via logger.exception()

**Helper function moved**: `is_valid_journal_filename()` moved from server.py to utils.py (no longer private with underscore prefix).

**Code cleanup**: Removed unused `__main__` blocks and `__all__` exports from __init__.py.

**Tests updated**: Added 5 tests for ProjectInput model validation (40 total tests now).

**Documentation updated**: README.md expanded with project workflow examples and vault structure. CLAUDE.md updated with logging details.

### Current Session

**Knowledge management added**: User requested knowledge guide support for comprehensive topic documentation.

**Implementation details**:
- Added `list_knowledge_guides()` tool in server.py (~35 lines)
- Lists markdown files in knowledge/ directory (flat structure, no subdirectories)
- Filters to .md files only, alphabetically sorted
- Uses existing `list_files_in_directory()` utility with recursive=False
- No input validation needed (no parameters)
- Follows existing patterns (mirrors projects approach)

**Testing added**:
- Added `setup_knowledge_guides()` fixture in conftest.py
- Added `TestKnowledgeTools` class in test_e2e.py with 5 tests:
  - Empty directory handling
  - Listing guides with content
  - Markdown file filtering (non-.md files ignored)
  - Reading guides via read_file
  - Writing guides via write_file
- Total tests increased from 40 to 45
- All tests pass in < 1 second

**Documentation updated**:
- README.md: Added knowledge workflow section, updated vault structure diagram, updated tool count
- CLAUDE.md: Updated scope, filesystem organization, tool list, test breakdown, feature history

**Design rationale**:
- Minimal surface area: one listing tool only (read/write already work)
- Flat structure enforced (no subdirectories)
- Descriptive filenames (no metadata, no frontmatter parsing)
- Consistent with existing patterns (same approach as projects)

That's it. Simple project, simple rules.
