this MCP server gives Claude Desktop access to an [Obsidian](https://obsidian.md) vault for three main workflows: daily journal entries using the [daily notes](https://help.obsidian.md/plugins/daily-notes) feature, project-based document organization, and knowledge management with comprehensive markdown guides.

the server assumes your vault is organized like this:

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
│   ├── home automation/
│   │   ├── requirements.md
│   │   ├── architecture.md
│   │   └── device list.md
│   ├── blog redesign/
│   │   ├── design.md
│   │   └── content structure.md
│   └── obsidian mcp/
│       ├── roadmap.md
│       └── design decisions.md
└── knowledge/
    ├── python asyncio.md
    ├── docker networking.md
    ├── git workflows.md
    └── kubernetes basics.md
```

## setup

this mcp server runs in a docker container for use with claude desktop.

#### get the docker image

```bash
docker pull ghcr.io/vicgarcia/obsidian-mcp:latest
```

#### configure claude desktop or claude code

**claude desktop**: add this to your mcp settings:

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
        "ghcr.io/vicgarcia/obsidian-mcp:latest"
      ]
    }
  }
}
```

**claude code**: use the cli to add the server:

```bash
claude mcp add --scope user --transport stdio obsidian -- \
  docker run --rm -i \
  -u $(id -u):$(id -g) \
  -v /path/to/your/vault:/vault \
  -e TZ=America/New_York \
  ghcr.io/vicgarcia/obsidian-mcp:latest
```

replace the following:
- `1000:1000` with your user:group IDs (run `id` command to find yours)
- `/path/to/your/vault` with the absolute path to your obsidian vault
- `America/New_York` with your timezone (e.g., `America/Chicago`, `Europe/London`)

optional: add `-e "LOG_LEVEL=debug"` to the args for detailed logging

## usage

#### journal workflow

the typical workflow is asking claude to help write or update today's journal entry. claude can:
- get today's journal path
- read existing content
- help draft or expand entries
- list entries from specific months
- read past entries for context

#### project workflow

claude can help organize and manage project documents:
- list all projects
- browse files within a project
- create new project directories
- read and write project documentation
- search across project files

#### knowledge workflow

claude can help maintain comprehensive topic guides:
- list all knowledge guides
- read existing guides for reference
- create new guides on specific topics
- update and expand existing documentation

knowledge guides use descriptive filenames with spaces in lowercase (e.g., `python asyncio.md`, `docker networking.md`) and live in a flat directory structure for easy discovery.

#### available prompts

**daily notes session**
- `daily_notes_session` - start an interactive session for daily note-taking
  - announces today's date and confirms with user
  - collects notes throughout the day with thoughtful follow-up questions
  - generates comprehensive journal entries when you're ready
  - handles catching up on previous days through conversation

#### available tools

**file operations**
- `read_file(file_path)` - read any file in the vault
- `write_file(file_path, content)` - write to any file in the vault

**journal operations**
- `list_todays_journal_entry()` - get the path for today's entry
- `list_journal_entries_by_year_and_month(year, month)` - list entries for a specific month

**project operations**
- `list_projects()` - list all project directories
- `list_project_content(project)` - list files within a project
- `create_project(project)` - create a new project directory

**knowledge operations**
- `list_knowledge_guides()` - list all knowledge guides

#### security

path validation prevents access outside your vault. all file operations are checked against the vault root directory. docker runs with your user permissions, so file ownership stays correct.

## dev

if you want to work on this locally:

```bash
git clone https://github.com/vicgarcia/obsidian-mcp
cd obsidian-mcp

# install dependencies
uv sync

# run tests
uv run pytest
```

#### project structure

```
src/
  obsidian_mcp/
    __init__.py       # package marker
    server.py         # mcp tools implementation + run() entry point
    models.py         # input validation
    utils.py          # helper functions

tests/
  conftest.py         # pytest fixtures
  test_e2e.py         # end-to-end tests
  test_models.py      # validation tests
  test_utils.py       # utility tests
```

#### building docker image locally

```bash
docker build -t ghcr.io/vicgarcia/obsidian-mcp:local .
```

to use the local build in claude desktop, update your mcp settings

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
        "ghcr.io/vicgarcia/obsidian-mcp:local"
      ]
    }
  }
}
```
