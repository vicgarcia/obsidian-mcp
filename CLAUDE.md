# Claude Code Project Context

## Project Overview

This is an MCP server for Obsidian journal management. It's intentionally minimal - built to do one thing well rather than trying to handle every possible Obsidian use case.

The server provides Claude Desktop with access to journal entries organized in a year/month filesystem structure. That's the entire scope.

## Current Status

Production ready. 4 tools implemented, all tests passing, Docker deployment configured.

This is feature-complete by design. The goal was simplicity, not comprehensiveness.

## Design Philosophy

### Why Journal-Only

Most Obsidian MCP servers try to expose everything - knowledge bases, projects, tags, templates, etc. That creates complexity and maintenance overhead for features I don't actually use.

I use Obsidian primarily for daily journaling. The daily notes feature combined with a simple filesystem hierarchy (year/month) is all I need. So that's all this server does.

### Filesystem Organization

Journal entries are organized as:
```
journal/YYYY/MM/YYYY-MM-DD.md
```

This structure is rigid by design. It keeps things predictable and makes date-based queries straightforward. The MCP tools assume this structure exists.

### Simplicity Over Features

Every removed feature is a decision to keep the codebase maintainable:
- No templates (don't need them)
- No knowledge management (separate tools handle this better)
- No project tracking (not my workflow)
- No tag support (filesystem is enough)
- No complex queries (just list and read)

Each removed feature means less code to maintain, fewer edge cases, and faster execution.

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

Everything is in one server file. No need to split journal/knowledge/projects when there's only journal.

### Key Decisions

**Pydantic for validation**: Explicit input models catch bad data early. All path inputs, date formats, and file operations go through validation.

**Docker-first deployment**: Simpler than managing Python environments. User permissions map cleanly through Docker's --user flag.

**Timezone awareness**: Journal entries need to respect local time, not UTC. The TZ environment variable handles this.

**No abstraction layers**: Direct path manipulation with pathlib. No ORMs, no query builders, just file operations.

## MCP Tools (4 total)

**General file operations**:
- `read_file` - read any file in vault
- `write_file` - write to any file in vault

**Journal operations**:
- `list_todays_journal_entry` - get path for today
- `list_journal_entries_by_year_and_month` - list entries for YYYY/MM

That's it. No create/delete/move operations. Read and write cover the journal workflow.

## Code Style

Non-negotiable conventions:
- Comments in lowercase (except proper names/symbols)
- Docstrings use triple single quotes: `''' like this '''`
- Single-line docstrings have spaces: `''' text '''`
- Files end with blank line

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

## Security

**Path validation**: All file paths validated against vault root using `pathlib.Path.is_relative_to()`. No traversal attacks.

**Input sanitization**: Pydantic models validate formats before any file operations.

**Principle of least privilege**: Docker runs as specified user, not root. File permissions stay correct.

## Testing

29 tests covering:
- Input validation (models)
- Path operations (utils)
- File operations (e2e)
- Journal tools (e2e)

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

## What Was Removed

Originally had:
- Templates system (templates.py)
- Knowledge base tools (knowledge.py)
- Project management (projects.py)
- Docker Compose setup
- Coverage testing
- Native installation paths

All removed to keep scope tight. Each removal was deliberate.

## Context for Future Sessions

- This is feature-complete by design
- Focus is maintenance and bug fixes, not new features
- Don't re-add removed functionality without explicit request
- Architecture decisions were intentional, not accidental
- Simplicity is the goal, not comprehensiveness

If someone asks to add knowledge management or project tools, the answer is no unless they fork it. This does journal entries, that's the scope.

## Development Workflow

1. Changes go through tests first
2. Code style rules are non-negotiable
3. Keep dependencies minimal
4. Docker is the deployment path
5. Don't break the 4-tool interface

That's it. Simple project, simple rules.
