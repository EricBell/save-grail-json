"""
Command-line interface for save-grail-json.
"""

import sys
from pathlib import Path
from typing import List
import click

from src import __version__
from src.config import DatabaseConfig, ConfigError
from src.database import GrailDatabase, DatabaseError
from src.ingestion import ingest_json_file, IngestionError


@click.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True))
@click.option(
    '--tui',
    is_flag=True,
    help='Launch interactive TUI file browser'
)
@click.option(
    '--config',
    type=click.Path(exists=True),
    help='Path to database configuration file (overrides default)'
)
@click.option(
    '--database',
    help='Database name (overrides config file setting)'
)
@click.version_option(version=__version__, prog_name='save-grail-json')
def main(files: tuple, tui: bool, config: str, database: str):
    """
    Save grail JSON files to PostgreSQL database for later review and analysis.

    \b
    Examples:
        save-grail-json file1.json file2.json
        save-grail-json data/*.json
        save-grail-json --tui
        save-grail-json --config /path/to/config.toml file.json
    """
    # Check for TUI mode
    if tui:
        launch_tui(config, database)
        return

    # CLI mode requires files
    if not files:
        click.echo("Error: No files specified. Use --tui for interactive mode or provide file paths.")
        click.echo("Run 'save-grail-json --help' for usage information.")
        sys.exit(1)

    # Load configuration
    try:
        db_config = DatabaseConfig(config)
    except ConfigError as e:
        click.echo(f"Configuration Error: {e}", err=True)
        sys.exit(1)

    # Process files
    process_files(list(files), db_config, database)


def process_files(file_paths: List[str], db_config: DatabaseConfig, database_name: str = None):
    """
    Process and ingest JSON files.

    Args:
        file_paths: List of file paths to process
        db_config: Database configuration
        database_name: Optional database name override
    """
    total_files = len(file_paths)
    inserted_count = 0
    updated_count = 0
    duplicate_count = 0
    error_count = 0

    click.echo(f"Processing {total_files} file(s)...\n")

    try:
        with GrailDatabase(db_config, database_name) as db:
            for file_path in file_paths:
                try:
                    # Ingest the file
                    file_data = ingest_json_file(file_path)

                    # Insert/update in database
                    result = db.insert_grail_file(
                        file_path=file_data.file_path,
                        json_content=file_data.json_content,
                        content_hash=file_data.content_hash,
                        ticker=file_data.ticker,
                        asset_type=file_data.asset_type,
                        file_created_at=file_data.file_created_at,
                        file_modified_at=file_data.file_modified_at
                    )

                    if result == 'inserted':
                        click.echo(f"✓ {file_path} (new)")
                        inserted_count += 1
                    elif result == 'updated':
                        click.echo(f"↻ {file_path} (updated)")
                        updated_count += 1
                    elif result == 'duplicate':
                        click.echo(f"⊘ {file_path} (duplicate content, skipped)")
                        duplicate_count += 1

                except IngestionError as e:
                    click.echo(f"✗ {file_path}: {e}", err=True)
                    error_count += 1

                except DatabaseError as e:
                    click.echo(f"✗ {file_path}: Database error: {e}", err=True)
                    error_count += 1

    except DatabaseError as e:
        click.echo(f"\nFatal database error: {e}", err=True)
        sys.exit(1)

    # Summary
    click.echo(f"\n{'='*60}")
    click.echo(f"Inserted (new):        {inserted_count} file(s)")
    if updated_count > 0:
        click.echo(f"Updated (changed):     {updated_count} file(s)")
    if duplicate_count > 0:
        click.echo(f"Skipped (duplicates):  {duplicate_count} file(s)")
    if error_count > 0:
        click.echo(f"Errors:                {error_count} file(s)")
    click.echo(f"{'='*60}")

    if error_count > 0:
        sys.exit(1)


def launch_tui(config_path: str = None, database_name: str = None):
    """
    Launch the interactive TUI file browser.

    Args:
        config_path: Optional config file path
        database_name: Optional database name override
    """
    try:
        from src.tui import GrailFileBrowser
    except ImportError as e:
        click.echo(f"Error: Failed to import TUI module: {e}", err=True)
        click.echo("Make sure textual is installed: pip install textual", err=True)
        sys.exit(1)

    # Load configuration
    try:
        db_config = DatabaseConfig(config_path)
    except ConfigError as e:
        click.echo(f"Configuration Error: {e}", err=True)
        sys.exit(1)

    # Launch TUI
    app = GrailFileBrowser(db_config, database_name)
    app.run()


if __name__ == '__main__':
    main()
