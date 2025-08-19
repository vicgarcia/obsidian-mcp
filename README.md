# Obsidian MCP Server

A Model Context Protocol (MCP) server that provides Claude Desktop with seamless access to Obsidian vaults. This server acts as a bridge between Claude's AI capabilities and Obsidian's rich note ecosystem, enabling intelligent interactions with personal knowledge bases.

## Features

- **📝 Journal Management**: Structured daily note-taking with hierarchical date organization
- **🧠 Knowledge Base**: Topic-based organization for research and reference materials  
- **📋 Project Management**: Project-based organization for active work and documentation
- **🔒 Security First**: Comprehensive path validation and security measures
- **🐳 Docker Ready**: Containerized deployment for easy setup and portability
- **⚡ FastMCP Framework**: Built on the FastMCP Python framework for optimal performance

## Installation

### Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install from Source

```bash
# Clone the repository
git clone <repository-url>
cd obsidian-mcp

# Install with uv (recommended)
uv sync
uv run obsidian-mcp

# Or install with pip
pip install -e .
obsidian-mcp
```

### Installation

```bash
# Build the Docker image
./build.sh

# Test the image (optional)
docker run --rm \
  --user "$(id -u):$(id -g)" \
  -v "/path/to/your/vault:/vault" \
  -e OBSIDIAN_VAULT_PATH=/vault \
  obsidian-mcp:local
```


## Configuration

The server requires the `OBSIDIAN_VAULT_PATH` environment variable to be set to your Obsidian vault directory:

```bash
export OBSIDIAN_VAULT_PATH="/path/to/your/obsidian/vault"
obsidian-mcp
```

## Claude Desktop Integration

First, build the Docker image:

```bash
./build.sh
```

Add this configuration to your Claude Desktop MCP settings:

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--user", "1000:1000",
        "-v", "/path/to/your/obsidian/vault:/vault",
        "-e", "OBSIDIAN_VAULT_PATH=/vault",
        "-e", "TZ=America/New_York",
        "obsidian-mcp:local"
      ]
    }
  }
}
```

**Configuration Notes:**

- Replace `/path/to/your/obsidian/vault` with the absolute path to your Obsidian vault
- Replace `1000:1000` with your actual user:group IDs (run `id` to find them)
- Replace `America/New_York` with your timezone (e.g., `America/Chicago`, `America/Los_Angeles`)
- Make sure your Obsidian vault directory has proper read/write permissions
- The vault path must be accessible to Docker

**Example:**

```json
{
  "mcpServers": {
    "obsidian": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--user", "501:20",
        "-v", "/Users/username/Documents/MyVault:/vault",
        "-e", "OBSIDIAN_VAULT_PATH=/vault",
        "-e", "TZ=America/New_York",
        "obsidian-mcp:local"
      ]
    }
  }
}
```

## Vault Structure

The server expects and manages the following directory structure:

```
vault/
├── journal/
│   ├── 2025/
│   │   ├── 01/
│   │   │   ├── 2025-01-01.md
│   │   │   └── 2025-01-02.md
│   │   └── 02/
│   └── 2024/
├── knowledge/
│   ├── machine-learning/
│   │   ├── neural-networks.md
│   │   └── papers/
│   └── philosophy/
│       └── ethics.md
└── projects/
    ├── website-redesign/
    │   ├── requirements.md
    │   └── assets/
    └── mobile-app/
        └── user-stories.md
```

## Available Tools

### General File Operations

- **`read_file`**: Read file content from the vault
- **`write_file`**: Write content to a file in the vault

### Journal Tools

- **`list_todays_journal_entry`**: Get today's journal entry path
- **`list_journal_entries_by_year_and_month`**: List journal entries for a specific month

### Knowledge Tools

- **`list_knowledge_topics`**: List all knowledge topic directories
- **`list_topic_content`**: List all files within a knowledge topic
- **`create_topic`**: Create a new knowledge topic directory

### Project Tools

- **`list_projects`**: List all project directories
- **`list_project_content`**: List all files within a project
- **`create_project`**: Create a new project directory

## Usage Examples

### Working with Journal Entries

```python
# Get today's journal entry path
today_entry = list_todays_journal_entry()
# Returns: {"path": "journal/2025/01/2025-01-19.md", "name": "2025-01-19.md"}

# Read today's journal entry
content = read_file("journal/2025/01/2025-01-19.md")

# Create or update today's journal entry
write_file("journal/2025/01/2025-01-19.md", "# My thoughts today...")

# List all journal entries for January 2025
entries = list_journal_entries_by_year_and_month("2025", "01")
```

### Managing Knowledge Base

```python
# List all knowledge topics
topics = list_knowledge_topics()
# Returns: [{"path": "knowledge/machine-learning", "name": "machine-learning"}, ...]

# Create a new topic
create_topic("quantum-computing")

# List content in a topic
content = list_topic_content("machine-learning")
# Returns: [{"path": "knowledge/machine-learning/neural-networks.md", "name": "neural-networks.md"}, ...]

# Read a knowledge file
neural_nets = read_file("knowledge/machine-learning/neural-networks.md")
```

### Project Management

```python
# List all projects
projects = list_projects()

# Create a new project
create_project("ai-assistant")

# List project content
content = list_project_content("website-redesign")

# Read project requirements
requirements = read_file("projects/website-redesign/requirements.md")
```

## Security Features

- **Path Validation**: All file paths are validated against the vault root directory
- **Directory Traversal Prevention**: Prevents access outside the vault using path resolution
- **Input Sanitization**: Comprehensive validation using Pydantic models
- **Read-Before-Write**: File modifications require reading current content first
- **Error Handling**: Standardized error responses with descriptive messages

## Development

### Running Tests

```bash
# Quick test run
uv run pytest

# Full test suite
./run_tests.sh

# Run specific test files
uv run pytest tests/test_utils.py
uv run pytest tests/test_e2e.py
```

### Development Setup

```bash
# Clone and install in development mode
git clone <repository-url>
cd obsidian-mcp
uv sync --dev

# Build Docker image for testing
./build.sh

# Run with development vault
export OBSIDIAN_VAULT_PATH="$(pwd)/tests/fixtures/vault"
uv run obsidian-mcp
```

### Project Structure

```
src/obsidian_mcp/
├── __init__.py          # Package initialization
├── server.py           # Main MCP server and general file operations
├── models.py           # Pydantic models for input validation
├── utils.py            # Utility functions and helpers
├── journal.py          # Journal-specific tools
├── knowledge.py        # Knowledge base tools
└── projects.py         # Project management tools

tests/
├── conftest.py         # Test configuration and fixtures
├── test_utils.py       # Unit tests for utility functions  
├── test_models.py      # Tests for Pydantic models
├── test_e2e.py         # End-to-end integration tests
└── fixtures/           # Test data and vault structure
```

## Error Handling

All tools return standardized error responses:

```json
{"error": "Descriptive error message"}
```

Common error scenarios:
- File not found
- Invalid date formats
- Path validation failures
- Permission errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section below

## Troubleshooting

### Vault Path Issues

If you get "OBSIDIAN_VAULT_PATH environment variable is required":
- Ensure the environment variable is set correctly
- Check that the path exists and is readable
- Use absolute paths rather than relative paths

### Docker Issues

If the Docker container fails to start:
- Verify the vault volume mount path
- Check that the vault directory has proper permissions
- Ensure Docker has access to the vault directory

### Import Errors

If you get import errors:
- Ensure all dependencies are installed (`uv sync` or `pip install -e .`)
- Check that Python 3.12+ is being used
- Verify the source directory structure is intact