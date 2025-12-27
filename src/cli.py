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
                        file_modified_at=file_data.file_modified_at,
                        # Core fields
                        status=file_data.status,
                        error_message=file_data.error_message,
                        trade_style=file_data.trade_style,
                        account_size=file_data.account_size,
                        risk_percent=file_data.risk_percent,
                        # Trading decision
                        should_trade=file_data.should_trade,
                        trade_action=file_data.trade_action,
                        trade_confidence_text=file_data.trade_confidence_text,
                        trade_confidence_pct=file_data.trade_confidence_pct,
                        no_trade_reason=file_data.no_trade_reason,
                        # Entry fields
                        entry_direction=file_data.entry_direction,
                        entry_price=file_data.entry_price,
                        entry_recommendation=file_data.entry_recommendation,
                        # Position sizing
                        position_quantity=file_data.position_quantity,
                        position_unit_type=file_data.position_unit_type,
                        position_size_recommendation=file_data.position_size_recommendation,
                        position_total_cost_text=file_data.position_total_cost_text,
                        position_max_risk_text=file_data.position_max_risk_text,
                        # Market context
                        market_status=file_data.market_status,
                        is_tradeable_now=file_data.is_tradeable_now,
                        in_trial=file_data.in_trial,
                        # API tracking
                        runs_remaining=file_data.runs_remaining,
                        daily_runs_remaining=file_data.daily_runs_remaining,
                        # Ticker resolution
                        resolved_ticker=file_data.resolved_ticker,
                        resolved_ticker_method=file_data.resolved_ticker_method,
                        # Agent confidence
                        technical_confidence=file_data.technical_confidence,
                        macro_confidence=file_data.macro_confidence,
                        wild_card_risk=file_data.wild_card_risk,
                        agent_agreement=file_data.agent_agreement,
                        # Options-specific
                        option_contract_symbol=file_data.option_contract_symbol,
                        option_type=file_data.option_type,
                        option_strike=file_data.option_strike,
                        option_expiration=file_data.option_expiration,
                        option_days_to_expiry=file_data.option_days_to_expiry,
                        option_delta=file_data.option_delta,
                        option_mid_price=file_data.option_mid_price,
                        option_volume=file_data.option_volume,
                        option_open_interest=file_data.option_open_interest
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
