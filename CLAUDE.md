# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**save-grail-json** is a Python tool to collect and organize grail JSON files for later review and analysis. The tool operates in two modes:
1. **CLI Mode**: Batch ingestion of specified JSON files
2. **TUI Mode**: Interactive filesystem browser for file selection

**Important:** See `PRD.md` for complete product requirements, data model, and architecture decisions.

This project is licensed under the GNU General Public License v3 (GPL-3.0), which means all derivative works must also be open source under GPL-3.0.

## Project Status

This is a new project in early development. Source code, dependencies, and build configuration have not yet been implemented.

## Database Configuration

The application uses PostgreSQL for storage. Database credentials are stored in `~/.config/postgres/save-grail-json.toml`:

```toml
[server]
host = "hostname"
port = 5432
user = "username"
password = "password"
database = "grail_files"  # Optional
```

**Configuration Pattern:** This app follows a standard convention where each app stores its database config in `~/.config/postgres/<app-name>.toml`.

**Setup:**
```bash
# Copy from existing default config or create new
cp ~/.config/postgres/default.toml ~/.config/postgres/save-grail-json.toml
chmod 600 ~/.config/postgres/save-grail-json.toml
```

**Override:** Use `--config` flag or `GRAIL_DB_CONFIG` environment variable to specify alternate config file.

## Development Commands

### Installation
```bash
# Install in development mode
pip install -e .

# Or install dependencies directly
pip install -r requirements.txt
```

### Running the Application
```bash
# CLI mode - ingest specific files
python -m src.cli file1.json file2.json

# CLI mode - with glob patterns
python -m src.cli data/*.json

# TUI mode - interactive file browser
python -m src.cli --tui

# Custom config file
python -m src.cli --config /path/to/config.toml file.json

# Custom database name
python -m src.cli --database my_database file.json

# After installation via pip install -e .
save-grail-json file1.json
save-grail-json --tui
```

### Testing
```bash
# Run tests (when implemented)
pytest tests/

# Run specific test file
pytest tests/test_ingestion.py
```

### Linting/Formatting
```bash
# Format code
black src/

# Lint code
ruff check src/

# Type checking
mypy src/
```

## Architecture

### Technology Stack
- **Language:** Python 3.8+
- **Database:** PostgreSQL
- **TUI Framework:** Textual
- **Dependencies:** psycopg2/psycopg3, tomli/tomllib

### Module Structure
- `src/__init__.py` - Package initialization
- `src/cli.py` - Command-line interface using Click
  - Main entry point with `main()` function
  - Handles CLI and TUI mode selection
  - File processing and progress reporting
- `src/config.py` - TOML configuration loading
  - `DatabaseConfig` class loads from `~/.config/postgres/save-grail-json.toml`
  - Supports config override via `--config` flag or `GRAIL_DB_CONFIG` env var
  - Validates required fields (host, port, user, password)
- `src/database.py` - PostgreSQL connection and operations
  - `GrailDatabase` class with context manager support
  - Creates database and table schema if needed
  - `insert_grail_file()` handles duplicate detection via UNIQUE constraint
- `src/ingestion.py` - JSON file reading and field extraction
  - `GrailFileData` dataclass for extracted information
  - `ingest_json_file()` reads JSON and extracts ticker, asset_type
  - Gets file creation/modification timestamps
- `src/tui.py` - Interactive file browser using Textual
  - `GrailFileBrowser` app with directory tree navigation
  - Arrow keys (↑/↓) to navigate files and directories
  - Enter to expand/collapse directories
  - 'u' key or button to navigate up to parent directory
  - Space to select/deselect JSON files
  - 'i' key or button to ingest selected files
  - Real-time status updates and error handling

### Data Flow
1. User specifies files (CLI) or selects files (TUI)
2. System reads JSON file and extracts: `ticker`, `asset_type`
3. System captures file timestamps from filesystem
4. Complete JSON stored as text in PostgreSQL with extracted metadata
5. Database enforces uniqueness by file_path (no duplicates)

### Key Design Decisions
- PostgreSQL for robust querying and future scalability
- TOML config for database credentials (user home directory)
- Full JSON preservation for future analysis
- Textual framework for cross-platform TUI support
