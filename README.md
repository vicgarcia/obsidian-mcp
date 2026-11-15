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

#### get_todays_date

get today's date and the current time in your timezone (`TZ`):

```json
{
  "date": "2026-11-14",
  "time": "14:32",
  "day_of_week": "Saturday",
  "timezone": "America/New_York"
}
```

`date` is the format the journal tools take. claude is told to call this before touching the journal instead of guessing the date, and to check the time: after midnight you may still mean the previous day

**example usage in claude:**
> "what's today's date?"

#### list_journal_entries_by_year_and_month

list all journal entries for a specific month

**parameters:**
- `year` (required): year in YYYY format
- `month` (required): month in MM format (e.g., "01", "10")

**example usage in claude:**
> "show me my journal entries from january 2025"

#### read_journal_entry

read the journal entry for a date; returns its `path`, `exists: false` and empty content when there is no entry

**parameters:**
- `date` (required): date in YYYY-MM-DD format

**example usage in claude:**
> "what did i write in my journal on october 3rd?"

#### journal format

a day's file has a `# Daily Notes` section that notes are added to through the day, each stamped with the time it was added. other top-level sections, such as a daily recap, go above it. no date heading, obsidian handles that. this guidance is sent to claude as server instructions

```markdown


# Daily Recap
a good, busy day...

# Daily Notes
### Morning run
first-person narrative...
2026-11-14 07:50

### obsidian-mcp refactor
#### Work
...
#### Notes
- links, commands, snippets, todos
2026-11-14 15:40

```

a new file starts as two blank lines and `# Daily Notes`. the file is always written with `\n` line endings, on mac and windows alike

#### add_note_to_journal_entry

add a note to the `# Daily Notes` section, the usual way to write to the journal. the note starts with a `###` heading naming its topic, then the note on the next line, organized with `####` and `#####` if it's long; `#` and `##` headings are rejected (outside code blocks). the tool:

- creates the file as `\n\n# Daily Notes\n` if it's missing or empty, or appends `# Daily Notes` to a file that doesn't have it
- trims the note, then appends it followed by a newline, the timestamp (`YYYY-MM-DD HH:MM`, 24-hour), and two newlines
- stamps the current time even when `date` is an earlier day, so a note written at 00:45 for yesterday shows when it was really written

**parameters:**
- `text` (required): the note, starting with a `###` heading
- `date` (optional): date in YYYY-MM-DD format, defaults to today

**example usage in claude:**
> "add a note: the new trail by the river is great for running"
> "it's 1am but i haven't slept, add a note to today about the deploy" (claude confirms and passes yesterday's date)

#### write_journal_entry / append_to_journal_entry / prepend_to_journal_entry

lower-level ways to edit a journal file, each creating the file if needed:

- **write_journal_entry**: replace the whole file (read it first, used for editing or reorganizing existing content)
- **append_to_journal_entry**: write text at the end of the file exactly as given, with nothing added or trimmed. existing content is never rewritten
- **prepend_to_journal_entry**: write text at the top of the file exactly as given, right after any yaml frontmatter, with nothing added or trimmed. used for sections above the notes, such as a recap; end the text with a blank line to separate it

**parameters:**
- `content` / `text` (required): markdown to write, append, or prepend
- `date` (optional): date in YYYY-MM-DD format, defaults to today

**example usage in claude:**
> "add a daily recap to the top of today's journal"

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
