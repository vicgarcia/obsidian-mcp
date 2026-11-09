This MCP server gives Claude Desktop access to an [Obsidian](https://obsidian.md) vault for three main workflows: daily journal entries, project-based document organization, and a wiki for comprehensive markdown articles.

Once set up, you can make queries like:

- "what did I work on last week?"
- "list my projects"
- "read the docker networking wiki article"

## setup

#### configure your vault

the server assumes your vault is organized like this:

```
vault/
├── journal/
│   └── 2025/
│       ├── 01/
│       │   ├── 2025-01-15.md
│       │   ├── 2025-01-16.md
│       │   └── 2025-01-17.md
│       └── 02/
│           ├── 2025-02-01.md
│           └── 2025-02-02.md
├── projects/
│   ├── home automation/
│   │   ├── architecture.md
│   │   ├── sensor notes.md
│   │   └── todo.md
│   └── blog redesign/
│       ├── requirements.md
│       └── wireframes.md
└── wiki/
    ├── docker networking.md
    ├── python asyncio.md
    └── git workflows.md
```

- **journal**: daily entries organized by `YYYY/MM/YYYY-MM-DD.md`
- **projects**: directories for ongoing work with related docs
- **wiki**: standalone articles on specific topics (flat structure)

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

## tools

this mcp server exposes 13 tools to interact with your obsidian vault.

#### read_file / write_file

read or write any file in the vault

**parameters:**
- `file_path` (required): vault-relative path to the file
- `content` (required for write): content to write

**example usage in claude:**
> "read the architecture.md file in my home automation project"

#### get_current_timestamp

get the current local date and time (using `TZ`) in every common format:

```json
{
  "iso": "2026-11-08T14:32:05-05:00",
  "utc": "2026-11-08T19:32:05Z",
  "unix": 1794166325,
  "date": "2026-11-08",
  "time": "14:32:05",
  "time_12h": "2:32 PM",
  "day_of_week": "Sunday",
  "human_date": "Sunday November 8, 2026",
  "human": "Sunday November 8, 2026 at 2:32 PM",
  "iso_week": "2026-W45",
  "timezone": "America/New_York",
  "utc_offset": "-05:00"
}
```

**example usage in claude:**
> "what's today's date?"
> "what time is it?"

#### list_todays_journal_entry

get the path for today's journal entry (e.g., `journal/2025/01/2025-01-15.md`)

**example usage in claude:**
> "what's my journal path for today?"

#### list_journal_entries_by_year_and_month

list all journal entries for a specific month

**parameters:**
- `year` (required): year in YYYY format
- `month` (required): month in MM format (e.g., "01", "10")

**example usage in claude:**
> "show me my journal entries from january 2025"

#### read_journal_entry

read the journal entry for a date; returns `exists: false` and empty content when there is no entry

**parameters:**
- `date` (required): date in YYYY-MM-DD format

**example usage in claude:**
> "what did i write in my journal on october 3rd?"

#### journal entry format

a day's file holds one or more entries. each entry starts with a `###` heading naming it, and uses `####` and `#####` headings to organize within it. no date heading, obsidian handles that. this guidance is sent to claude as server instructions and repeated in the journal tool descriptions

before touching a journal entry, claude is told to call `get_current_timestamp` instead of guessing the date, to confirm the date when you are writing after midnight or catching up on an earlier day, and to use the time of day for ordering without writing timestamps into entries

```markdown
### Morning run and MCP refactor

first-person narrative...

#### Work

##### obsidian-mcp
...

#### Notes
- links, commands, snippets, todos

### Evening reading
...
```

#### write_journal_entry / append_to_journal_entry / prepend_to_journal_entry

three ways to edit a journal file, each creating the file if needed:

- **write_journal_entry**: replace the whole file (read it first, used for editing or reorganizing existing entries)
- **append_to_journal_entry**: add text to the end, separated by a blank line. existing content is never rewritten
- **prepend_to_journal_entry**: add text to the top, after any yaml frontmatter. the rest of the file is kept unchanged

append and prepend keep the file's line endings (lf or crlf)

**parameters:**
- `content` / `text` (required): markdown to write, append, or prepend
- `date` (optional): date in YYYY-MM-DD format, defaults to today

**example usage in claude:**
> "add to my journal: the new trail by the river is great for running"
> "add an entry to the top of yesterday's journal about the dentist visit"

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
├── src/obsidian_mcp/
│   ├── __init__.py       # package init, version
│   ├── server.py         # FastMCP server + 13 tools
│   ├── vault_client.py   # vault operations (context manager)
│   └── schema.py         # pydantic validation models
├── tests/
│   ├── conftest.py       # pytest fixtures
│   ├── test_schema.py
│   ├── test_vault_client.py
│   ├── test_tools.py
│   └── test_integration.py
├── pyproject.toml
├── Dockerfile
└── README.md
```

#### building docker image locally

```bash
docker build -t obsidian-mcp:local .
```

to use the local build in claude desktop, update your mcp settings to use `obsidian-mcp:local` instead of `ghcr.io/vicgarcia/obsidian-mcp:latest`.
