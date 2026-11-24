# Claude Code Session Documentation

## Project Overview
Obsidian MCP Server - A modular Python MCP server for accessing an Obsidian vault in Claude Desktop. Built with MCP, implements 14 core tools for journal entries, projects, and wiki articles. Intentionally minimal to keep context usage low and let Claude handle interpretation.

Installed via `uv tool install` only (no Docker).

## Project Structure
```
obsidian-mcp/
├── src/
│   └── obsidian_mcp/
│       ├── __init__.py       # package init, version, exports
│       ├── server.py         # FastMCP server + 14 tools
│       ├── vault_client.py   # vault operations (context manager)
│       └── schema.py         # Pydantic validation models
├── tests/
│   ├── conftest.py           # pytest fixtures
│   ├── test_schema.py        # validation model tests
│   ├── test_vault_client.py  # vault client tests
│   ├── test_tools.py         # MCP tool tests
│   ├── test_search.py        # journal search tests
│   ├── test_tool_metadata.py # tool order, annotations, argument descriptions
│   └── test_integration.py   # integration tests
├── pyproject.toml            # package metadata and dependencies
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
uv run pytest tests/ -v                   # run tests
```

### Installation
```bash
uv tool install git+https://github.com/vicgarcia/obsidian-mcp
```

### Environment Variables
- `OBSIDIAN_VAULT_PATH`: Path to vault (or use --vault flag)
- `TZ`: Timezone for journal dates (e.g., America/New_York)
- `LOG_LEVEL`: Optional. DEBUG or INFO (default: INFO)

## Tools Overview
Fourteen core MCP tools (see README.md for full documentation):
- `read_file` / `write_file` - General file operations
- `get_todays_date` - Today's date, 12-hour time with AM/PM, day of the week and timezone (TZ)
- `list_journal_entries_by_year_and_month` - List entries for a month
- `read_journal_entry` - Read an entry by date
- `add_note_to_journal_entry` - Append a note to the end of the entry, after two blank lines (an empty file starts with the note). The tool adds no section heading. The note must start with a `###` heading; nothing else about its headings is checked. The note's content is written exactly as sent (only its ends are trimmed); the tool description gives the agent the layout (a blank line after every heading and before every heading after the first). Then comes a blank line, a `YYYY-MM-DD HH:MM` timestamp line and two blank lines (optional `date`, defaults to today; the stamp is always the current time)
- `write_journal_entry` / `append_to_journal_entry` / `prepend_to_journal_entry` - Replace, append to, or prepend to an entry. Append and prepend write the text byte for byte, adding and trimming nothing; prepend goes right after YAML frontmatter
- `search_journal` - Keyword search over journal notes, newest day first. Each `###` note (plus any text above the first one) is matched on its own; every query word must appear in it, ignoring case, and `"quoted phrases"` match exactly. Optional `start_date` / `end_date` (inclusive) and `max_results` (1-50, default 20). Returns date, path, heading, timestamp and a ~200 char snippet per note, with `total_matches` and `truncated`. Scans the files on every call; no index
- `list_projects` / `list_project_content` / `create_project` - Project management
- `list_wiki` - List wiki articles

Journal format guidance lives in `JOURNAL_FORMAT` in server.py, which is passed as the FastMCP server `instructions`: `###` notes (`####` / `#####` within) appended through the day, with sections such as a recap prepended above them. It ends with a short section on projects and the wiki (which paths `read_file` / `write_file` take, and that documenting something means the journal plus a project file).

What clients see about each tool is set in server.py, not left to a gateway: tools are defined in the order they are listed (usual ones first, `add_note_to_journal_entry` at the top); every tool has `ToolAnnotations` (`READ_ONLY`, `ADDS` = not destructive, `REPLACES` = destructive, all `openWorldHint=False`); every argument is `Annotated[..., Field(description=...)]`, so docstrings carry no `Args:` block. `test_tool_metadata.py` enforces all three. Docstrings say what a tool returns in a closing sentence ("Returns a dictionary with ..."), not a `Returns:` section, and give examples after "For example:", not an `Example:` section: fastmcp 4 strips those sections from tool descriptions. Every journal write uses `newline=''` so files stay LF on Windows.

## Implementation Notes

### Architecture Decisions
- **Modular package structure**: Separation of concerns into distinct modules
- **VaultClient context manager**: Clean resource management for vault operations
- **Schema module**: Centralized Pydantic validation models
- **MCP FastMCP**: Used for MCP server framework (simpler than raw MCP protocol)
- **STDIO Transport**: Default for Claude Desktop compatibility
- **Single deployment**: `uv tool install` only

### Module Organization

#### schema.py (Data Models)
- `YearMonthInput` - Year/month validation
- `JournalDateInput` / `JournalTextInput` / `JournalWriteInput` / `JournalNoteInput` - Journal date and edit validation (optional date defaults to today; `JournalTextInput` keeps text exact, `JournalNoteInput` requires a leading `###` and rejects `#`/`##` outside code fences)
- `JournalSearchInput` / `parse_search_terms()` - Search query (words and quoted phrases), date range and result limit validation
- `FilePathInput` - File path validation with traversal protection
- `FileWriteInput` - File write input validation
- `ProjectInput` - Project name validation
- `create_error_response()` / `create_success_response()` - Response helpers

#### vault_client.py (Vault Operations)
- `VaultClient` - Context manager for all vault operations
- `VaultError` - Custom exception for vault errors
- File operations: `read_file()`, `write_file()`, `file_exists()`
- Directory operations: `list_files()`, `list_directories()`, `create_directory()`
- Journal operations: `get_journal_path()`, `list_journal_entries()`, `read_journal_entry()`, `write_journal_entry()`, `append_to_journal()`, `prepend_to_journal()`, `add_note_to_journal()`, `search_journal()`
- Journal search helpers: `split_journal_notes()` splits an entry on `###` lines outside code fences and pulls the timestamp line off each note
- Project operations: `list_projects()`, `list_project_content()`, `create_project()`
- Wiki operations: `list_wiki()`

#### server.py (MCP Server)
- FastMCP server initialization
- 14 `@mcp.tool(annotations=...)` definitions, in the order clients list them
- Module-level client singleton
- Entry point `run()` function

### Code Quality Features
- Type hints throughout
- Consistent error handling patterns: `{"error": "message", "success": False}`
- Structured logging with configurable levels (all lowercase except proper names)
- Path security validation, identical on macOS and Windows (the vault syncs between them). `validate_vault_path` in schema.py checks the text: `\` counts as `/`, no absolute, rooted, UNC or drive paths, no `..`/`.`/empty parts, and every name must be portable (`check_name`: no `< > : " | ? *` or control characters, which also rules out drive letters and NTFS streams; no reserved device names like `nul.md`; no trailing dot or space). `VaultClient._validate_path` runs that check for every caller, then resolves the path (following symlinks and junctions) and refuses anything outside the vault
- Responses never reveal where the vault lives: errors name vault-relative paths and an OSError's reason (`strerror`), not its text, and every server error goes through `error_response`, which redacts the vault root as a backstop. Full detail goes to the log only
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
- **14 tools**: Covering three workflows (files/journal, projects, wiki)
- **Strict filesystem structure**: `journal/YYYY/MM/`, `projects/`, `wiki/`
- **Single deployment**: uv tool install
- **Path validation**: Security-first file operations
- **Comprehensive test suite**: Tests generated on the fly

### What We Didn't Build
- No templates (just create files directly)
- No tag support (filesystem organization is enough)
- No complex queries (let Claude interpret); journal search is plain keyword matching, no regex, ranking or index
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
- Tests organized by module (test_schema.py, test_vault_client.py, test_tools.py), journal search in test_search.py
- Integration tests in test_integration.py
- Test data generated on the fly using pytest tmp_path
