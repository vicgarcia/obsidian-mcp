# Claude Code Project Context

## Project Overview

This is an MCP server for Obsidian vault management. It's intentionally minimal - built to handle journal entries, project tracking, and wiki articles without the complexity of full-featured Obsidian tools.

The server provides Claude Desktop and Claude Code with access to:
- Journal entries organized in a year/month filesystem structure (journal/YYYY/MM/)
- Project directories for organizing work (projects/)
- Wiki articles for comprehensive topic documentation (wiki/)
- General file read/write operations across the vault

## Current Status

Production ready. 10 tools implemented, 45 tests passing, Docker deployment configured.

This is feature-complete by design. The goal was simplicity, not comprehensiveness.

## Design Philosophy

### Scope: Journal, Projects, and Wiki

Most Obsidian MCP servers try to expose everything - tags, templates, complex queries, graph analysis, etc. That creates complexity and maintenance overhead.

This server focuses on three core workflows:
1. **Journal entries**: Daily notes with strict YYYY/MM/DD filesystem hierarchy
2. **Project tracking**: Simple directory-based organization for ongoing work
3. **Wiki articles**: Flat directory of comprehensive topic documentation (obsidian wiki)

No templates, no tag systems. Just files organized in predictable directories.

### Filesystem Organization

See README.md for vault structure diagram.

**Journal**: `journal/YYYY/MM/YYYY-MM-DD.md` - month always two digits (01-12), rigid by design for predictable date queries.

**Projects**: `projects/project name/` - flat hierarchy, no nesting, use spaces instead of hyphens in names (e.g., `home automation/`, `blog redesign/`).

**Wiki**: `wiki/topic name.md` - flat structure, descriptive filenames with spaces in lowercase (e.g., `python asyncio.md`, `docker networking.md`), no metadata/frontmatter.

### Simplicity Over Features

Every omitted feature is a decision to keep the codebase maintainable:
- No templates (just create files directly)
- No tag support (filesystem organization is enough)
- No complex queries (just list and read)
- No file deletion/moving (use read/write instead)
- No subdirectories in wiki (flat structure only)
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

## MCP Interface

**Tools (10 total)**
2 general file operations + 4 journal + 3 project + 1 wiki = 10 tools total.

No delete/move operations by design. Read and write handle all file modifications. See README.md for detailed tool descriptions.

## Code Style

Non-negotiable conventions:
- Comments in lowercase (except proper names/symbols)
- Docstrings use triple single quotes: `''' like this '''`
- Single-line docstrings have spaces: `''' text '''`
- Files end with blank line
- No file-level docstrings (removed for simplicity)
- Log messages in lowercase (except proper names like YYYY, TZ, etc.)

## Deployment

Docker only. No native installation because Docker handles dependencies and permissions cleanly.

**Why Docker-only**:
- User permissions map cleanly via --user flag (prevents file ownership issues)
- No Python environment management
- Same deployment for Desktop and Code
- GitHub Actions builds/publishes to GHCR automatically

**Image naming**:
- Production: `ghcr.io/vicgarcia/obsidian-mcp:latest`
- Local dev: `ghcr.io/vicgarcia/obsidian-mcp:local` (via ./build.sh)

**Setup details**: See README.md for full Claude Desktop and Claude Code configuration commands.

**Environment variables**:
- `TZ` (required) - timezone for journal date calculations (e.g., America/New_York)
- `LOG_LEVEL` (optional) - debug or info, defaults to info
- `OBSIDIAN_VAULT_PATH` - set internally to /vault, not needed in user config

## Security

**Path validation**: All file paths validated against vault root using `pathlib.Path.is_relative_to()`. No traversal attacks.

**Input sanitization**: Pydantic models validate formats before any file operations.

**Principle of least privilege**: Docker runs as specified user, not root. File permissions stay correct.

## Testing

46 tests covering:
- Input validation (models) - 14 tests
- Path operations (utils) - 11 tests
- File operations (e2e) - 6 tests
- Journal tools (e2e) - 3 tests
- Project tools (e2e) - 5 tests
- Wiki tools (e2e) - 5 tests
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

## Context for Future Sessions

- This is feature-complete by design
- Focus is maintenance and bug fixes, not new features
- Don't add removed functionality (templates) without explicit request
- Architecture decisions were intentional, not accidental
- Simplicity is the goal, not comprehensiveness

Current scope: journal entries + project tracking + wiki articles. No templates, no complex queries, no metadata parsing.

## Development Workflow

1. Changes go through tests first
2. Code style rules are non-negotiable
3. Keep dependencies minimal
4. Docker is the deployment path
5. Don't break the 10-tool interface

## Entry Points

- **Console script**: `obsidian-mcp` (configured in pyproject.toml)
- **Main function**: `obsidian_mcp.server.run()`
- **Package import**: `from obsidian_mcp import run`
- **No `__main__` blocks**: Entry point configured via pyproject.toml only
- **No `__all__` exports**: Keep imports simple

That's it. Simple project, simple rules.
