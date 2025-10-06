This is an MCP server for managing daily journal entries in [Obsidian](https://obsidian.md). I use the [daily notes](https://help.obsidian.md/plugins/daily-notes) feature to maintain a journal of markdown files organized by a year and month. This MCP server gives Claude Desktop access to that journal structure so it can help me generate and manage daily entries.

The server assumes the journal is organized like this :

```
vault/
└── journal/
    └── 2025/
        ├── 01/
        │   ├── 2025-01-01.md
        │   ├── 2025-01-02.md
        │   └── ...
        ├── 02/
        └── ...
```

## Installation

Build the Docker image:

```bash
./build.sh
```

## Configuration

Add this to your Claude Desktop MCP settings. Replace the paths and IDs with your own:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--user", "1000:1000",
        "-v", "/path/to/your/vault:/vault",
        "-e", "TZ=America/New_York",
        "obsidian-mcp:local"
      ]
    }
  }
}
```

Notes:
- Run `id` to get your user:group IDs and replace 1000:1000
- Use your actual timezone (e.g., `America/Chicago`, `Europe/London`)

## Usage

The typical workflow is asking Claude to help write or update today's journal entry. Claude can:
- Get today's journal path
- Read existing content
- Help draft or expand entries
- List entries from specific months
- Read past entries for context

### Available Tools

**File Operations**
- `read_file` - read any file in the vault
- `write_file` - write to any file in the vault

**Journal Operations**
- `list_todays_journal_entry` - get the path for today's entry
- `list_journal_entries_by_year_and_month` - list entries for a specific month

### Security

Path validation prevents access outside your vault. All file operations are checked against the vault root directory. Docker runs with your user permissions, so file ownership stays correct.

## Development

Run tests:
```bash
uv run pytest
```

The project structure is simple:
```
src/obsidian_mcp/
├── server.py    # MCP server and all tools
├── models.py    # input validation
└── utils.py     # helper functions

tests/
├── conftest.py
├── test_e2e.py
├── test_models.py
└── test_utils.py
```

## Troubleshooting

**Vault path issues**: Make sure `OBSIDIAN_VAULT_PATH` points to your actual vault directory and that Docker can access it.

**Permission errors**: Check that your `--user` flag matches your actual user:group IDs from the `id` command.

**Wrong dates**: Set the `TZ` environment variable to your local timezone.
