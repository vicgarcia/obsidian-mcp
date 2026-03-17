This MCP server gives Claude Desktop access to an [Obsidian](https://obsidian.md) vault for four main workflows: daily journal entries, project-based document organization, a wiki for comprehensive markdown articles, and agent prompts for LLM instructions.

Once set up, you can make queries like:

- "start a daily notes session"
- "what did I work on last week?"
- "list my projects"
- "read the docker networking wiki article"
- "use the code review assistant prompt"

## setup

#### configure your vault

the server assumes your vault is organized like this:

```
vault/
├── journal/YYYY/MM/YYYY-MM-DD.md   # daily journal entries
├── projects/project name/           # project directories with docs
├── wiki/topic name.md              # standalone wiki articles
└── prompts/prompt name.md          # agent prompt files
```

#### option 1: install with uv

```bash
uv tool install git+https://github.com/vicgarcia/obsidian-mcp
```

claude desktop config:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "obsidian-mcp",
      "args": ["--vault", "/path/to/your/vault"]
    }
  }
}
```

#### option 2: docker

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/path/to/your/vault:/vault",
        "-e", "TZ=America/New_York",
        "ghcr.io/vicgarcia/obsidian-mcp:latest"
      ]
    }
  }
}
```

replace `/path/to/your/vault` with the absolute path to your obsidian vault

## features

this mcp server exposes tools to interact with your obsidian vault.

#### read_file / write_file

read or write any file in the vault

**parameters:**
- `file_path` (required): vault-relative path to the file
- `content` (required for write): content to write

**example usage in claude:**
> "read the architecture.md file in my home automation project"

#### get_current_date

get the current date in both YYYY-MM-DD and human-readable formats

**example usage in claude:**
> "what's today's date?"

#### list_todays_journal_entry

get the path for today's journal entry (e.g., `journal/2025/01/2025-01-15.md`)

**example usage in claude:**
> "what's my journal path for today?"

#### start_daily_notes_session

start an interactive daily notes workflow that announces the date, collects notes throughout the day with follow-up questions, and generates a narrative journal entry

**example usage in claude:**
> "start a daily notes session"

#### list_journal_entries_by_year_and_month

list all journal entries for a specific month

**parameters:**
- `year` (required): year in YYYY format
- `month` (required): month in MM format (e.g., "01", "10")

**example usage in claude:**
> "show me my journal entries from january 2025"

#### list_projects / list_project_content / create_project

manage project directories in your vault

**parameters:**
- `project` (required): name of the project directory

**example usage in claude:**
> "list my projects"
> "show me the files in my home automation project"
> "create a new project called blog redesign"

#### list_wiki

list all wiki articles in the wiki directory

**example usage in claude:**
> "list my wiki articles"

#### list_prompts / read_prompt

access agent prompts stored in your vault

**parameters:**
- `prompt` (required for read): filename of the prompt

**example usage in claude:**
> "list my prompts"
> "read the code review assistant prompt"

## development

```bash
git clone https://github.com/vicgarcia/obsidian-mcp
cd obsidian-mcp

# install in editable mode
uv tool install --editable .

# run
obsidian-mcp --vault /path/to/vault

# run tests
uv run pytest
```

#### project structure

```
obsidian-mcp/
├── obsidian_mcp.py       # single-file module (server + all logic)
├── obsidian_mcp_test.py  # tests
├── pyproject.toml        # package metadata and dependencies
├── Dockerfile            # docker deployment
└── README.md
```

#### building docker image locally

```bash
docker build -t obsidian-mcp:local .
```

to use the local build in claude desktop, update your mcp settings to use `obsidian-mcp:local` instead of `ghcr.io/vicgarcia/obsidian-mcp:latest`.
