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

To be documented once the project structure is established. Typical commands will include:
- Installation/setup
- Running tests
- Linting/formatting
- Building/deploying

## Architecture

### Technology Stack
- **Language:** Python 3.8+
- **Database:** PostgreSQL
- **TUI Framework:** Textual
- **Dependencies:** psycopg2/psycopg3, tomli/tomllib

### Module Structure (Planned)
- `cli.py` - Command-line interface and argument parsing
- `config.py` - TOML configuration loading
- `database.py` - PostgreSQL connection and operations
- `ingestion.py` - JSON file reading and field extraction
- `tui.py` - Interactive file browser using Textual

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
