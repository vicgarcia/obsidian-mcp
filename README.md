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

#### install with uv

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

replace `/path/to/your/vault` with the absolute path to your obsidian vault

## tools

this mcp server exposes 14 tools to interact with your obsidian vault. every tool is annotated as read-only, adding content, or replacing content, and every argument has a description, so clients can decide when to ask before a call. tools are listed with the usual ones first, starting with add_note_to_journal_entry.

#### read_file / write_file

read or write any file in the vault

paths are relative to the vault root and can't leave it, with the same rules on macos and windows: no absolute, drive or network paths, no `..`, and no names windows can't hold (`:` `?` `*` and the like, reserved names such as `nul.md`, a trailing dot or space). `\` works as a separator. links that point out of the vault are refused. errors never show where the vault is on disk

**parameters:**
- `file_path` (required): vault-relative path to the file
- `content` (required for write): content to write

<sub>example usage with agent:</sub>
> "read the architecture.md file in my home automation project"

#### get_todays_date

get today's date and the current time in your timezone (`TZ`):

```json
{
  "date": "2026-11-14",
  "time": "2:32 PM",
  "day_of_week": "Saturday",
  "timezone": "America/New_York"
}
```

`date` is the format the journal tools take. claude is told to call this before touching the journal instead of guessing the date, and to check the time: after midnight you may still mean the previous day

<sub>example usage with agent:</sub>
> "what's today's date?"

#### list_journal_entries_by_year_and_month

list all journal entries for a specific month

**parameters:**
- `year` (required): year in YYYY format
- `month` (required): month in MM format (e.g., "01", "10")

<sub>example usage with agent:</sub>
> "show me my journal entries from january 2025"

#### read_journal_entry

read the journal entry for a date; returns its `path`, `exists: false` and empty content when there is no entry

**parameters:**
- `date` (required): date in YYYY-MM-DD format

<sub>example usage with agent:</sub>
> "what did i write in my journal on october 3rd?"

#### journal format

notes are added to the end of a day's file through the day, each stamped with the time it was added. anything that belongs above them, such as a daily recap, is prepended. no date heading, obsidian handles that. this guidance is sent to claude as server instructions

```markdown
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

the file is always written with `\n` line endings, on mac and windows alike

#### add_note_to_journal_entry

add a note to the end of a journal entry, the usual way to write to the journal. the note must start with a `###` heading naming its topic, or it's rejected. the tool description asks the agent to organize a long note with `####` and `#####`; those aren't checked. the agent sends only the note; the tool handles the spacing around it and the timestamp:

- a missing or empty file starts with the note. otherwise the file gets whatever newlines make it end in two blank lines, then the note
- the note's content is written exactly as the agent sends it, spacing included; only its ends are trimmed. the tool description gives the agent the layout to use: a blank line after every heading, and a blank line before every heading after the first
- the note is appended followed by a blank line, the timestamp (`YYYY-MM-DD HH:MM`, 24-hour) and two blank lines, so notes sit two blank lines apart
- the timestamp is the current time even when `date` is an earlier day, so a note written at 00:45 for yesterday shows when it was really written

**parameters:**
- `text` (required): the note, starting with a `###` heading
- `date` (optional): date in YYYY-MM-DD format, defaults to today

<sub>example usage with agent:</sub>
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

<sub>example usage with agent:</sub>
> "add a daily recap to the top of today's journal"

#### search_journal

search journal notes by keyword, newest day first. each `###` note is matched on its own, so every word in the query has to appear in the same note (text above the first note, such as a recap, counts as one more). matching ignores case and line breaks; put words in double quotes to match an exact phrase. there's no index, the journal files are scanned on each call

each result has the entry `date` and `path`, the note's `heading` and `timestamp`, and a short `snippet` around the first match. claude reads the full day with `read_journal_entry`. `total_matches` and `truncated` say when more notes matched than were returned

**parameters:**
- `query` (required): words to find, e.g. `dentist insurance` or `"river trail" run`
- `start_date` / `end_date` (optional): YYYY-MM-DD, inclusive
- `max_results` (optional): 1 to 50, defaults to 20

<sub>example usage with agent:</sub>
> "when did i last write about the dentist?"
> "find my notes about the river trail from last spring"

#### list_projects / list_project_content / create_project

manage project directories in your vault

**parameters:**
- `project` (required): name of the project directory

<sub>example usage with agent:</sub>
> "list my projects"
> "show me the files in my home automation project"
> "create a new project called blog redesign"

#### list_wiki

list all wiki articles in the wiki directory. the server instructions explain that list_project_content and list_wiki give the paths read_file and write_file take

<sub>example usage with agent:</sub>
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
│   ├── server.py         # FastMCP server + 14 tools
│   ├── vault_client.py   # vault operations (context manager)
│   └── schema.py         # pydantic validation models
├── tests/
│   ├── conftest.py       # pytest fixtures
│   ├── test_schema.py
│   ├── test_vault_client.py
│   ├── test_tools.py
│   ├── test_search.py
│   ├── test_tool_metadata.py
│   └── test_integration.py
├── pyproject.toml
└── README.md
```
