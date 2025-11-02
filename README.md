I have three main workflows using [Obsidian](https://obsidian.md): daily journal entries using the [daily notes](https://help.obsidian.md/plugins/daily-notes) feature, project-based document organization, and knowledge management with comprehensive markdown guides.

This MCP server gives Claude Desktop access to all three workflows so it can help me generate journal entries, manage project files, and maintain knowledge documentation.

The server assumes the vault is organized like this:

```
vault/
├── journal/
│   └── 2025/
│       ├── 01/
│       │   ├── 2025-01-01.md
│       │   ├── 2025-01-02.md
│       │   └── 2025-01-15.md
│       ├── 02/
│       └── 10/
│           └── 2025-10-06.md
├── projects/
│   ├── home-automation/
│   │   ├── requirements.md
│   │   ├── architecture.md
│   │   └── device-list.md
│   ├── blog-redesign/
│   │   ├── design.md
│   │   └── content-structure.md
│   └── obsidian-mcp/
│       ├── roadmap.md
│       └── design-decisions.md
└── knowledge/
    ├── python-asyncio.md
    ├── docker-networking.md
    ├── git-workflows.md
    └── kubernetes-basics.md
```

## Installation

Clone the repository:

```bash
git clone https://github.com/vicgarcia/obsidian-mcp.git
cd obsidian-mcp
```

Build the Docker image:

```bash
docker build -t obsidian-mcp:local .
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
- Set `LOG_LEVEL=debug` in the environment variables for detailed logging

## Usage

### Journal Workflow

The typical workflow is asking Claude to help write or update today's journal entry. Claude can:
- Get today's journal path
- Read existing content
- Help draft or expand entries
- List entries from specific months
- Read past entries for context

### Project Workflow

Claude can help organize and manage project documents:
- List all projects
- Browse files within a project
- Create new project directories
- Read and write project documentation
- Search across project files

### Knowledge Workflow

Claude can help maintain comprehensive topic guides:
- List all knowledge guides
- Read existing guides for reference
- Create new guides on specific topics
- Update and expand existing documentation

Knowledge guides use descriptive filenames (e.g., `python-asyncio.md`, `docker-networking.md`) and live in a flat directory structure for easy discovery.

### Available Tools

**File Operations**
- `read_file(file_path)` - read any file in the vault
- `write_file(file_path, content)` - write to any file in the vault

**Journal Operations**
- `list_todays_journal_entry()` - get the path for today's entry
- `list_journal_entries_by_year_and_month(year, month)` - list entries for a specific month

**Project Operations**
- `list_projects()` - list all project directories
- `list_project_content(project)` - list files within a project
- `create_project(project)` - create a new project directory

**Knowledge Operations**
- `list_knowledge_guides()` - list all knowledge guides

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

**Debugging**: Set `LOG_LEVEL=debug` in your Docker environment variables to see detailed logging output. Add `-e "LOG_LEVEL=debug"` to the Docker args in your Claude Desktop config.
