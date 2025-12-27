# Product Requirements Document: save-grail-json

## 1. Project Overview

**Project Name:** save-grail-json

**Purpose:** A Python tool to collect and organize grail JSON files for later review and analysis. The tool ingests JSON files, extracts key metadata, and stores both the metadata and complete file content in a database.

**Current Phase:** Collection and organization
**Future Phase:** Analysis (to be defined later)

## 2. Objectives

- Provide a simple, efficient way to ingest JSON files containing financial/trading data
- Extract and index key fields for future querying
- Preserve complete JSON content for later detailed analysis
- Support both automated batch processing and interactive file selection

## 3. User Stories

### Story 1: CLI Batch Ingestion
**As a** user with multiple JSON files
**I want to** specify one or more files on the command line
**So that** they are ingested and stored in the database in a single operation

### Story 2: Interactive File Selection
**As a** user exploring my filesystem
**I want to** use an interactive TUI to navigate directories and select JSON files
**So that** I can visually browse and choose files for ingestion

### Story 3: Data Retrieval (Future)
**As a** user with collected data
**I want to** query and analyze the stored JSON files
**So that** I can extract insights from the collected information

## 4. Functional Requirements

### 4.1 Core Ingestion

- **FR-1.1:** The system shall accept one or more JSON file paths as input
- **FR-1.2:** The system shall read and parse each JSON file
- **FR-1.3:** The system shall extract the following fields from JSON content:
  - `ticker` (string)
  - `asset_type` (string)
- **FR-1.4:** The system shall capture file metadata:
  - File creation timestamp
  - File modification timestamp
- **FR-1.5:** The system shall store the complete JSON file content as text
- **FR-1.6:** The system shall handle missing fields gracefully (store NULL/None if field not present)
- **FR-1.7:** The system shall prevent duplicate ingestion of the same file

### 4.2 CLI Mode

- **FR-2.1:** The system shall provide a command-line interface accepting file paths as arguments
- **FR-2.2:** The system shall accept multiple file paths in a single invocation
- **FR-2.3:** The system shall support glob patterns (e.g., `*.json`)
- **FR-2.4:** The system shall display progress/status for each file processed
- **FR-2.5:** The system shall report errors for invalid/unreadable files without stopping processing

**Example Usage:**
```bash
save-grail-json file1.json file2.json file3.json
save-grail-json data/*.json
```

**CLI Output Format:**
The CLI provides clear status indicators for each file:
- `✓ file.json (new)` - File successfully inserted as new record
- `↻ file.json (updated)` - Existing file updated with new content
- `⊘ file.json (duplicate content, skipped)` - Same content already exists in database
- `✗ file.json: error message` - Error during processing

**Summary Report:**
After processing, a summary is displayed showing:
- Inserted (new): Count of new files added
- Updated (changed): Count of existing files updated
- Skipped (duplicates): Count of duplicate content skipped
- Errors: Count of files that failed processing

### 4.3 TUI Mode

- **FR-3.1:** The system shall provide an interactive terminal user interface
- **FR-3.2:** The TUI shall display the current directory and its contents
- **FR-3.3:** The TUI shall allow navigation up to parent directory via 'u' key
- **FR-3.4:** The TUI shall allow navigation down into subdirectories
- **FR-3.5:** The TUI shall highlight JSON files for selection
- **FR-3.6:** The TUI shall allow single or multiple file selection
- **FR-3.7:** The TUI shall start from the current working directory
- **FR-3.8:** The TUI shall provide a visual indicator of selected files
- **FR-3.9:** The TUI shall provide an action to ingest all selected files
- **FR-3.10:** The TUI shall display ingestion progress and results

**Example Usage:**
```bash
save-grail-json --tui
```

**TUI Controls:**
- ↑/↓: Navigate files and directories
- Enter: Expand/collapse directories
- u: Go up to parent directory
- Space: Select/deselect JSON files
- i: Ingest selected files
- q: Quit

### 4.4 Configuration Management

- **FR-4.1:** The system shall read database credentials from `~/.config/postgres/save-grail-json.toml`
- **FR-4.2:** The system shall allow config file override via `--config` flag or `GRAIL_DB_CONFIG` environment variable
- **FR-4.3:** The system shall fail gracefully with a clear error if the config file is missing
- **FR-4.4:** The system shall validate required configuration fields (host, port, user, password)
- **FR-4.5:** The system shall support optional database name override in config or CLI
- **FR-4.6:** The system shall create the target database if it doesn't exist (with appropriate permissions)
- **FR-4.7:** The system shall create the required table schema on first run if it doesn't exist

### 4.5 Version Management

- **FR-5.1:** The system shall maintain version information in `pyproject.toml` as the single source of truth
- **FR-5.2:** The system shall sync version information to `src/__init__.py` for runtime access
- **FR-5.3:** The system shall support manual version increment commands (major, minor, patch)
- **FR-5.4:** The system shall automatically increment patch version when tracked files change
- **FR-5.5:** The system shall use git pre-commit hooks to detect file changes and update version
- **FR-5.6:** The system shall track file hashes to detect changes in source files
- **FR-5.7:** The system shall display version via `--version` CLI flag
- **FR-5.8:** The system shall include version in installed package metadata

**Version Management Commands:**
```bash
# Check current version
python version_manager.py status
# Output: Current version: v0.2.0

# Manually increment patch version (0.2.0 → 0.2.1)
python version_manager.py patch

# Manually increment minor version (0.2.1 → 0.3.0)
python version_manager.py minor

# Manually increment major version (0.3.0 → 1.0.0)
python version_manager.py major

# Reset to specific version
python version_manager.py reset 1 0 0

# Check for changes and auto-increment if needed
python version_manager.py check
```

**Version Display:**
```bash
# Display installed version
save-grail-json --version
# Output: save-grail-json, version 0.2.0

# Display version with uv
uv run save-grail-json --version
```

**Git Hook Installation:**
```bash
# Install pre-commit hook for automatic version incrementing
./install-hooks.sh
# Output: Pre-commit hook installed at .git/hooks/pre-commit
```

**Automatic Versioning Workflow:**
1. Developer modifies source files in `src/**/*.py` or `pyproject.toml`
2. Developer commits changes: `git add . && git commit -m "message"`
3. Pre-commit hook runs `version_manager.py check`
4. If tracked files changed, patch version increments (e.g., 0.2.0 → 0.2.1)
5. Both `pyproject.toml` and `src/__init__.py` are updated
6. Updated version files are automatically staged in the commit
7. Commit proceeds with version bump included

### 4.6 Testing Requirements

- **FR-8.1:** The system shall include unit tests for configuration loading and validation
- **FR-8.2:** The system shall include unit tests for JSON ingestion and field extraction
- **FR-8.3:** The system shall include unit tests for database operations (insert, update, duplicate detection)
- **FR-8.4:** The system shall include integration tests for CLI mode operations
- **FR-8.5:** The system shall include integration tests for database schema creation and migrations
- **FR-8.6:** The system shall provide sample JSON files for testing and demonstration purposes
- **FR-8.7:** Tests shall be runnable via `uv run pytest tests/`
- **FR-8.8:** Tests shall use a separate test database to avoid affecting production data

### 4.7 Development and Maintenance Utilities

- **FR-9.1:** The system shall provide a `drop-tables.py` utility for development database cleanup
- **FR-9.2:** The drop tables utility shall only affect the grail_files table (safe for development)
- **FR-9.3:** The system shall provide an `install-hooks.sh` script for setting up git hooks
- **FR-9.4:** The git pre-commit hook shall automatically increment version on file changes

## 5. Data Model

### 5.1 Database Schema

**Database:** `grail_files` (default, configurable)

**Table: grail_files**

| Column | Type | Description | Constraints |
|--------|------|-------------|-------------|
| id | SERIAL | Primary key | PRIMARY KEY |
| ticker | VARCHAR(20) | Stock/asset ticker symbol | NULLABLE |
| asset_type | VARCHAR(50) | Type of asset (STOCK, etc.) | NULLABLE |
| file_path | TEXT | Original file path | NOT NULL, UNIQUE |
| content_hash | VARCHAR(64) | SHA256 hash of JSON content | NOT NULL, UNIQUE |
| file_created_at | TIMESTAMP | File creation timestamp | NULLABLE |
| file_modified_at | TIMESTAMP | File modification timestamp | NULLABLE |
| json_content | JSONB | Complete JSON file in binary format | NOT NULL |
| ingested_at | TIMESTAMP | When record was added to DB | DEFAULT CURRENT_TIMESTAMP |
| updated_at | TIMESTAMP | When record was last updated | DEFAULT CURRENT_TIMESTAMP |

**Indexes:**
- `idx_ticker` on `ticker` for faster searching
- `idx_asset_type` on `asset_type` for filtering
- `idx_ingested_at` on `ingested_at` for chronological queries
- `idx_content_hash` on `content_hash` for duplicate detection

**Schema Creation SQL:**
```sql
CREATE TABLE IF NOT EXISTS grail_files (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    asset_type VARCHAR(50),
    file_path TEXT NOT NULL UNIQUE,
    content_hash VARCHAR(64) NOT NULL UNIQUE,
    file_created_at TIMESTAMP,
    file_modified_at TIMESTAMP,
    json_content JSONB NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ticker ON grail_files(ticker);
CREATE INDEX IF NOT EXISTS idx_asset_type ON grail_files(asset_type);
CREATE INDEX IF NOT EXISTS idx_ingested_at ON grail_files(ingested_at);
CREATE INDEX IF NOT EXISTS idx_content_hash ON grail_files(content_hash);
```

**Key Schema Features:**
- **JSONB data type**: Enables efficient JSON querying, indexing, and validation
- **content_hash**: SHA256 hash for duplicate content detection (different from file_path)
- **updated_at**: Tracks when existing records are updated with new content

### 5.3 Duplicate Detection and Update Logic

**Duplicate Detection:**
The system uses a two-tier approach to prevent duplicates and handle updates:

1. **Content Hash Check**: SHA256 hash of JSON content
   - If same content exists (regardless of file path) → **Skip as duplicate**
   - Prevents ingesting identical JSON from different locations

2. **File Path Check**: Absolute file path
   - If same path exists with different content → **Update the record**
   - Allows tracking content changes over time

**Behavior Matrix:**

| Scenario | file_path | content_hash | Action | Result |
|----------|-----------|--------------|--------|--------|
| New file | Not exists | Not exists | INSERT | `inserted` |
| Same file, same content | Exists | Exists | SKIP | `duplicate` |
| Same file, changed content | Exists | Not exists | UPDATE | `updated` |
| Different file, same content | Not exists | Exists | SKIP | `duplicate` |

**Migration Support:**
- Existing databases without `content_hash` column are automatically migrated
- Migration computes hashes for all existing records
- TEXT to JSONB migration is automatic and transparent

### 5.2 Example JSON Structure

```json
{
  "status": "success",
  "ticker": "FENI",
  "requested_ticker": null,
  "resolved_ticker": null,
  "resolved_ticker_method": null,
  "asset_type": "STOCK",
  "trade_style": "DAY",
  "account_size": 10000,
  "risk_percent": 1
}
```

**Extracted Fields:**
- `ticker`: "FENI"
- `asset_type`: "STOCK"
- File timestamps: From filesystem

## 6. Technical Requirements

### 6.1 Technology Stack

- **Language:** Python 3.8+
- **TUI Framework:** Textual (https://textual.textualize.io/)
- **Database:** PostgreSQL
- **Database Driver:** psycopg2 or psycopg3
- **Configuration:** TOML for database credentials
- **CLI Framework:** argparse or Click
- **JSON Parsing:** Built-in `json` module

### 6.2 Dependencies

- `textual` - for TUI implementation
- `psycopg2-binary` or `psycopg` - PostgreSQL database driver
- `tomli` (Python < 3.11) or `tomllib` (Python 3.11+) - TOML parsing (read-only)
- `tomlkit` - TOML parsing with write support (preserves formatting)
- `click` - CLI framework with version option support
- Standard library modules: `json`, `pathlib`, `datetime`, `os`, `hashlib`, `re`

### 6.3 File Structure

```
save-grail-json/
├── src/
│   ├── __init__.py          # Package init, exports __version__
│   ├── cli.py               # CLI argument parsing and main entry point
│   ├── config.py            # Configuration loading from TOML
│   ├── database.py          # Database operations (PostgreSQL)
│   ├── ingestion.py         # JSON file reading and processing
│   └── tui.py               # TUI implementation with Textual
├── tests/                   # ⚠️ NOT YET IMPLEMENTED
│   ├── __init__.py
│   ├── test_config.py       # Tests for configuration loading
│   ├── test_ingestion.py    # Tests for JSON ingestion
│   ├── test_database.py     # Tests for database operations
│   ├── test_cli.py          # Integration tests for CLI
│   └── fixtures/            # Sample JSON files for testing
│       ├── valid_stock.json
│       ├── invalid_json.json
│       └── missing_fields.json
├── .git/
│   └── hooks/
│       └── pre-commit       # Git pre-commit hook for version auto-increment
├── version_manager.py       # Version management CLI and automation
├── install-hooks.sh         # Script to install git hooks
├── drop-tables.py           # Development utility to drop database tables
├── .version_hashes.json     # File hashes for change detection (gitignored)
├── .gitignore              # Git ignore patterns
├── pyproject.toml          # Project metadata and dependencies (source of version)
├── uv.lock                 # UV lockfile for reproducible installs
├── PRD.md                  # This document
├── CLAUDE.md               # Developer guidance
├── README.md               # ⚠️ Needs expansion with usage examples
└── LICENSE                 # GPL-3.0
```

### 6.4 Configuration

#### Database Credentials
- **Location:** `~/.config/postgres/save-grail-json.toml`
- **Format:** TOML configuration file
- **Pattern:** All apps using this credential mechanism store configs in `~/.config/postgres/<app-name>.toml`
- **Required fields:**
  ```toml
  [server]
  host = "hostname or IP"
  port = 5432
  user = "username"
  password = "password"
  ```
- **Optional fields:**
  ```toml
  [server]
  database = "grail_files"  # Default database name

  [metadata]
  created_at = "timestamp"
  description = "description"
  ```

#### Application Configuration
- TUI theme: Default Textual theme
- Logging: Console logging with configurable verbosity
- Database name: Default to `grail_files`, allow override via CLI flag `--database`
- Config file location: Allow override via `--config` flag or `GRAIL_DB_CONFIG` environment variable

## 7. Non-Functional Requirements

### 7.1 Performance
- Handle files up to 10MB efficiently
- Process multiple files with minimal memory overhead
- TUI should be responsive for directories with 1000+ files

### 7.2 Reliability
- Gracefully handle malformed JSON files
- Continue processing remaining files if one fails
- Maintain database consistency

### 7.3 Usability
- Clear error messages
- Intuitive TUI navigation
- Progress feedback during ingestion

### 7.4 Maintainability
- Modular code structure
- Unit tests for core functionality
- Type hints for better IDE support

### 7.5 Security
- Database credentials stored in user home directory with restricted permissions (chmod 600 recommended)
- No credentials in source code or logs
- Use parameterized queries to prevent SQL injection
- Secure connection to PostgreSQL server (SSL/TLS if configured in PostgreSQL)

## 8. Success Criteria

### Implemented (v0.2.0)
- ✅ Successfully ingest JSON files via CLI
- ✅ Successfully ingest JSON files via TUI
- ✅ Extract and store required fields (ticker, asset_type, timestamps)
- ✅ Store complete JSON content in JSONB format
- ✅ Navigate filesystem in TUI mode
- ✅ Handle errors gracefully without data loss
- ✅ Query stored data via basic SQL queries
- ✅ Content hash duplicate detection (SHA256)
- ✅ Update existing records when file content changes
- ✅ Automatic database and table creation
- ✅ Migration system for schema upgrades
- ✅ Version management with automatic incrementing

### Not Yet Implemented
- ❌ Unit tests for core functionality (FR-8.1 through FR-8.5)
- ❌ Comprehensive README with examples and usage guide
- ❌ Sample JSON files for testing and demonstration

## 9. Future Considerations

### Phase 2: Analysis Features (Not in MVP)
- Query interface for stored data
- Export functionality (CSV, Excel)
- Data visualization
- Duplicate detection and merging
- Bulk operations (delete, update)
- Search and filter capabilities
- Statistics and reporting

### Potential Enhancements
- Support for other data formats (CSV, XML)
- Alternative database backends (MongoDB, other SQL databases)
- Web interface
- Scheduled/automated ingestion
- Data validation rules
- Custom field extraction configuration
- Configuration profiles (multiple database servers)

## 10. Resolved Design Decisions

### 10.1 Duplicate Handling
**Question:** Should duplicate files (same path) be re-ingested or skipped?

**Decision:** Intelligent handling based on content hash:
- Same path + same content = Skip as duplicate
- Same path + different content = Update the existing record
- Different path + same content = Skip as duplicate (content already stored)

**Implementation:** Two-tier uniqueness constraint on both `file_path` and `content_hash`

### 10.2 Missing Field Handling
**Question:** How to handle files with missing ticker or asset_type fields?

**Decision:** Store as NULL with no warnings (optional fields)

**Rationale:** Not all JSON files will have these fields; system preserves complete JSON content regardless

### 10.3 TUI Recursive Selection
**Question:** Should the TUI allow recursive directory selection?

**Decision:** Phase 2 feature

**Current Implementation:** Manual navigation with 'u' key for parent directory

### 10.4 Database Backup Strategy
**Question:** What backup strategy should the system provide?

**Decision:** User responsibility; document PostgreSQL backup commands in README

**Rationale:** PostgreSQL provides robust backup tools (`pg_dump`, `pg_basebackup`); reinventing them is out of scope

### 10.5 Multiple Database Profiles
**Question:** Should database credentials support multiple profiles/servers?

**Decision:** Single profile in MVP; multi-profile support in Phase 2

**Current Implementation:** One config file at `~/.config/postgres/save-grail-json.toml`, overridable via `--config` flag

### 10.6 Storage Format
**Question:** Should JSON content be stored as TEXT or JSONB?

**Decision:** JSONB for query performance and validation

**Implementation:**
- JSONB storage enables PostgreSQL JSON operators and indexing
- Automatic migration from TEXT to JSONB for existing installations
- Complete JSON preservation regardless of format

## 11. Appendix

### A. Example CLI Sessions

**Single file ingestion:**
```bash
$ save-grail-json data/FENI.json
Processing: data/FENI.json... ✓
Successfully ingested 1 file(s)
```

**Multiple files with glob:**
```bash
$ save-grail-json data/*.json
Processing: data/FENI.json... ✓
Processing: data/AAPL.json... ✓
Processing: data/TSLA.json... ✓
Successfully ingested 3 file(s)
```

**With errors:**
```bash
$ save-grail-json data/*.json
Processing: data/FENI.json... ✓
Processing: data/invalid.json... ✗ (malformed JSON)
Processing: data/AAPL.json... ✓
Successfully ingested 2 file(s), 1 error(s)
```

### B. TUI Mockup (Text Description)

```
┌─ save-grail-json File Browser ────────────────────────────────────┐
│ Navigate with arrow keys. Press Space to select/deselect JSON    │
│ files. Press 'i' to ingest. Press 'u' for parent dir.            │
├───────────────────────────────────────────────────────────────────┤
│ ▼ 📁 trading-data                                                 │
│   ▼ 📁 2024-01                                                    │
│     ✓ 📄 FENI.json                                                │
│   ▼ 📁 2024-02                                                    │
│     ✓ 📄 AAPL.json                                                │
│     ☐ 📄 TSLA.json                                                │
│     ☐ 📄 notes.txt                                                │
├───────────────────────────────────────────────────────────────────┤
│ [Ingest Selected (i)] [Up to Parent (u)] [Quit (q)]              │
├───────────────────────────────────────────────────────────────────┤
│ Selected: 2 files                                                 │
└───────────────────────────────────────────────────────────────────┘
```

### C. Database Configuration File

**Location:** `~/.config/postgres/save-grail-json.toml`

**Pattern:** This app follows a standard convention where database credentials are stored in `~/.config/postgres/<app-name>.toml`. This allows multiple apps to maintain separate database configurations.

**Example:**
```toml
[server]
host = "192.168.1.249"
port = 32768
user = "postgres"
password = "your_secure_password"
database = "grail_files"  # Optional, defaults to "grail_files"

[metadata]
created_at = "2025-12-23T10:00:00.000000"
description = "PostgreSQL configuration for save-grail-json app"
```

**Setup:**
```bash
# Create the config directory if it doesn't exist
mkdir -p ~/.config/postgres

# Create the config file (copy from default.toml or create new)
cp ~/.config/postgres/default.toml ~/.config/postgres/save-grail-json.toml
# OR create from scratch
nano ~/.config/postgres/save-grail-json.toml

# Set secure permissions
chmod 600 ~/.config/postgres/save-grail-json.toml
```

**Override Options:**
```bash
# Use a different config file
save-grail-json --config /path/to/other-config.toml file.json

# Use environment variable
export GRAIL_DB_CONFIG=/path/to/other-config.toml
save-grail-json file.json
```

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-23 | Eric Bell / Claude | Initial PRD |
| 1.1 | 2025-12-23 | Eric Bell / Claude | Added PostgreSQL configuration |
| 1.2 | 2025-12-23 | Eric Bell / Claude | Changed config to `~/.config/postgres/save-grail-json.toml` (app-specific pattern) |
| 1.3 | 2025-12-23 | Eric Bell / Claude | Added TUI parent directory navigation ('u' key) |
| 1.4 | 2025-12-23 | Eric Bell / Claude | Added version management system (FR-5.1 through FR-5.8), version_manager.py, git hooks, updated dependencies and file structure |
| 1.5 | 2025-12-26 | Eric Bell / Claude | Comprehensive review update: Added testing requirements (FR-8.1-8.8), development utilities (FR-9.1-9.4), duplicate detection logic (Section 5.3), resolved design decisions (Section 10), updated success criteria to reflect implementation status, documented missing components (tests, comprehensive README) |
