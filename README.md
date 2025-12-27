# save-grail-json

A Python tool to collect and organize trading analysis JSON files in a PostgreSQL database for later review and analysis. Extract key metadata, preserve complete file content, and query your trading data with powerful SQL capabilities.

## Features

- **Dual Interface**: Use command-line batch mode or interactive TUI file browser
- **Smart Duplicate Detection**: Content-based hashing prevents duplicate ingestion
- **Rich Metadata Extraction**: Automatically extracts 48+ fields including ticker, asset type, trading decisions, position sizing, and options data
- **Complete Preservation**: Stores full JSON content in PostgreSQL's JSONB format for future analysis
- **Automatic Schema Management**: Creates databases and tables on first run, handles migrations automatically
- **File Change Tracking**: Updates existing records when file content changes

## Quick Start

### Installation

```bash
# Clone the repository
cd save-grail-json

# Install dependencies (creates virtual environment)
uv sync

# Run the CLI
uv run save-grail-json --help
```

### Database Configuration

Create a configuration file at `~/.config/postgres/save-grail-json.toml`:

```toml
[server]
host = "localhost"
port = 5432
user = "postgres"
password = "your_password"
database = "grail_files"  # Optional, defaults to "grail_files"
```

Set secure permissions:
```bash
chmod 600 ~/.config/postgres/save-grail-json.toml
```

> **Tip**: You can copy from an existing default config:
> ```bash
> mkdir -p ~/.config/postgres
> cp ~/.config/postgres/default.toml ~/.config/postgres/save-grail-json.toml
> ```

## Usage

### CLI Mode - Batch Processing

Ingest one or more JSON files from the command line:

```bash
# Single file
uv run save-grail-json trade-plan.json

# Multiple files
uv run save-grail-json file1.json file2.json file3.json

# Using glob patterns
uv run save-grail-json data/*.json

# Custom database or config
uv run save-grail-json --database my_db --config /path/to/config.toml data/*.json
```

**Output Example:**
```
Processing 3 file(s)...

✓ trade-plan-SPY-2025-12-23.json (new)
↻ trade-plan-MES-2025-12-26.json (updated)
⊘ trade-plan-duplicate.json (duplicate content, skipped)

============================================================
Inserted (new):        1 file(s)
Updated (changed):     1 file(s)
Skipped (duplicates):  1 file(s)
============================================================
```

### TUI Mode - Interactive File Browser

Launch the interactive file browser for visual file selection:

```bash
uv run save-grail-json --tui
```

**TUI Controls:**
- `↑/↓` - Navigate files and directories
- `Enter` - Expand/collapse directories
- `Space` - Select/deselect JSON files
- `u` - Navigate up to parent directory
- `i` - Ingest selected files
- `q` - Quit

## What Data Gets Extracted?

The tool extracts **48 fields** from your JSON files, organized into categories:

### Core Fields (17)
- Status, error messages, trade style
- Account size, risk percentage
- Trading decisions (should_trade, action, confidence)
- Market context (status, tradeability)
- API usage tracking

### Entry & Position Fields (8)
- Entry direction, price, recommendations
- Position quantity, unit type, sizing
- Cost and risk calculations

### Agent Confidence (4)
- Technical and macro confidence scores
- Wild card risk assessment
- Agent agreement metrics

### Options-Specific Fields (9)
- Contract symbol, type, strike, expiration
- Greeks (delta), pricing, volume
- Open interest

### Always Preserved
- Complete original JSON stored as JSONB
- File metadata (creation/modification times)
- Content hash for duplicate detection

## Database Schema

The tool automatically creates a PostgreSQL database with the following structure:

```sql
CREATE TABLE grail_files (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR(20),
    asset_type VARCHAR(50),
    file_path TEXT NOT NULL UNIQUE,
    content_hash VARCHAR(64) NOT NULL UNIQUE,

    -- 38 extracted metadata fields
    status VARCHAR(20),
    trade_style VARCHAR(20),
    should_trade BOOLEAN,
    trade_action VARCHAR(50),
    entry_price NUMERIC(12,4),
    -- ... (and 33 more fields)

    -- Complete JSON and timestamps
    json_content JSONB NOT NULL,
    file_created_at TIMESTAMP,
    file_modified_at TIMESTAMP,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes** are automatically created for fast querying on ticker, asset type, status, trade decisions, and more.

## Advanced Configuration

### Override Config File

Use a different configuration file:

```bash
# Via command-line flag
uv run save-grail-json --config /path/to/config.toml file.json

# Via environment variable
export GRAIL_DB_CONFIG=/path/to/config.toml
uv run save-grail-json file.json
```

### Custom Database Name

Override the default database name:

```bash
uv run save-grail-json --database my_trading_data file.json
```

## Querying Your Data

Once your files are ingested, use SQL to analyze your trading data:

```sql
-- Find all successful trades from the last week
SELECT ticker, asset_type, trade_action, trade_confidence_pct, entry_price
FROM grail_files
WHERE should_trade = true
  AND status = 'success'
  AND ingested_at > NOW() - INTERVAL '7 days'
ORDER BY ingested_at DESC;

-- Get average confidence by asset type
SELECT asset_type,
       AVG(trade_confidence_pct) as avg_confidence,
       COUNT(*) as total_trades
FROM grail_files
WHERE should_trade = true
GROUP BY asset_type;

-- Find all options trades with high delta
SELECT ticker, option_contract_symbol, option_strike,
       option_delta, option_mid_price
FROM grail_files
WHERE asset_type = 'OPTIONS'
  AND option_delta > 0.5
ORDER BY option_delta DESC;

-- Query the full JSON for custom analysis
SELECT ticker, json_content->'trade_plan'->'verdict'->>'reasoning' as reasoning
FROM grail_files
WHERE ticker = 'SPY'
  AND should_trade = true;
```

## Development Commands

```bash
# Install dependencies
uv sync

# Add a new dependency
uv add package-name

# Run tests (when implemented)
uv run pytest tests/

# Check current version
python version_manager.py status

# Format code
uv run black src/

# Type checking
uv run mypy src/
```

## How Duplicates Are Handled

The tool uses intelligent duplicate detection:

| Scenario | Behavior |
|----------|----------|
| New file | **Inserted** as new record |
| Same file, same content | **Skipped** (duplicate) |
| Same file, changed content | **Updated** (overwrites existing) |
| Different path, same content | **Skipped** (content already exists) |

This approach:
- Prevents duplicate content from cluttering your database
- Tracks changes to files over time
- Uses SHA256 content hashing for reliable detection

## Project Structure

```
save-grail-json/
├── src/
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Configuration loading
│   ├── database.py         # PostgreSQL operations
│   ├── ingestion.py        # JSON parsing and field extraction
│   └── tui.py              # Interactive file browser
├── examples/               # Sample JSON files
├── version_manager.py      # Version management
├── pyproject.toml         # Project metadata
└── README.md              # This file
```

## System Requirements

- Python 3.8+
- PostgreSQL database server
- Linux, macOS, or Windows with WSL

## License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0). See the [LICENSE](LICENSE) file for details.

All derivative works must also be licensed under GPL-3.0, ensuring the software remains free and open source.

## Troubleshooting

### Config file not found
**Error**: `Configuration Error: Config file not found`

**Solution**: Create the config file at `~/.config/postgres/save-grail-json.toml` with your database credentials.

### Permission denied
**Error**: `Permission denied` when accessing config file

**Solution**: Set correct permissions: `chmod 600 ~/.config/postgres/save-grail-json.toml`

### Database connection failed
**Error**: `Failed to connect to database`

**Solution**:
1. Verify PostgreSQL is running
2. Check host, port, username, and password in config file
3. Ensure user has permission to create databases

### Invalid JSON
**Error**: `Invalid JSON in file.json`

**Solution**: The file contains malformed JSON. Validate your JSON using a tool like `jsonlint` or fix syntax errors.

## Contributing

This is a personal project, but feedback and suggestions are welcome. Please open an issue on GitHub if you encounter problems or have ideas for improvements.

## Version

Current version: 0.2.0

Check your installed version:
```bash
uv run save-grail-json --version
```

---

**Note**: This tool is designed for collecting and organizing trading analysis files. Future versions may include analysis and reporting features.
