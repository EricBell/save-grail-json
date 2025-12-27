"""
Terminal User Interface for interactive file browsing and selection.
"""

import os
from pathlib import Path
from typing import List, Set

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, DirectoryTree, Static, Button
from textual.binding import Binding

from src.config import DatabaseConfig
from src.database import GrailDatabase, DatabaseError
from src.ingestion import ingest_json_file, IngestionError


class GrailFileBrowser(App):
    """Interactive file browser for selecting and ingesting JSON files."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #info-panel {
        height: 3;
        background: $panel;
        border: solid $primary;
        padding: 0 1;
    }

    #tree-container {
        height: 1fr;
        border: solid $primary;
    }

    #button-container {
        height: 3;
        layout: horizontal;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }

    #status {
        height: auto;
        background: $panel;
        padding: 0 1;
    }

    .success {
        color: $success;
    }

    .error {
        color: $error;
    }

    .warning {
        color: $warning;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("i", "ingest", "Ingest Selected"),
        Binding("u", "go_up", "Parent Dir"),
        ("escape", "quit", "Quit"),
    ]

    def __init__(self, db_config: DatabaseConfig, database_name: str = None):
        super().__init__()
        self.db_config = db_config
        self.database_name = database_name
        self.selected_files: Set[Path] = set()
        self.title = "Save Grail JSON - File Browser"
        self.current_path = Path(os.getcwd())

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Container(
            Static(
                "Navigate with arrow keys. Press Space to select/deselect JSON files. Press 'i' to ingest. Press 'u' for parent dir.",
                id="info-panel"
            ),
            Container(
                DirectoryTree(str(self.current_path), id="file-tree"),
                id="tree-container"
            ),
            Container(
                Button("Ingest Selected (i)", id="ingest-btn", variant="primary"),
                Button("Up to Parent (u)", id="up-btn", variant="default"),
                Button("Quit (q)", id="quit-btn", variant="default"),
                id="button-container"
            ),
            Static("", id="status"),
        )
        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount."""
        self.update_status()

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle file selection in the tree."""
        file_path = Path(event.path)

        # Only allow JSON files
        if file_path.suffix.lower() != '.json':
            self.update_status(f"Skipped: Only JSON files can be selected", "warning")
            return

        # Toggle selection
        if file_path in self.selected_files:
            self.selected_files.remove(file_path)
            self.update_status(f"Deselected: {file_path.name}")
        else:
            self.selected_files.add(file_path)
            self.update_status(f"Selected: {file_path.name}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "ingest-btn":
            self.action_ingest()
        elif event.button.id == "up-btn":
            self.action_go_up()
        elif event.button.id == "quit-btn":
            self.action_quit()

    def action_go_up(self) -> None:
        """Navigate to parent directory."""
        parent = self.current_path.parent

        # Check if we're already at root
        if parent == self.current_path:
            self.update_status("Already at root directory", "warning")
            return

        self.current_path = parent

        # Update the tree path
        try:
            tree = self.query_one("#file-tree", DirectoryTree)
            tree.path = str(self.current_path)
            self.update_status(f"Up to: {self.current_path}")

        except Exception as e:
            self.update_status(f"Error navigating up: {e}", "error")

    def action_ingest(self) -> None:
        """Ingest all selected files."""
        if not self.selected_files:
            self.update_status("No files selected. Navigate and press Space to select JSON files.", "warning")
            return

        files = list(self.selected_files)
        total = len(files)
        inserted = 0
        updated = 0
        duplicates = 0
        errors = 0

        self.update_status(f"Ingesting {total} file(s)...", "")

        try:
            with GrailDatabase(self.db_config, self.database_name) as db:
                for i, file_path in enumerate(files, 1):
                    try:
                        # Ingest the file
                        file_data = ingest_json_file(str(file_path))

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
                            inserted += 1
                            self.update_status(f"[{i}/{total}] ✓ {file_path.name} (new)", "success")
                        elif result == 'updated':
                            updated += 1
                            self.update_status(f"[{i}/{total}] ↻ {file_path.name} (updated)", "success")
                        elif result == 'duplicate':
                            duplicates += 1
                            self.update_status(f"[{i}/{total}] ⊘ {file_path.name} (duplicate)", "warning")

                    except (IngestionError, DatabaseError) as e:
                        errors += 1
                        self.update_status(f"[{i}/{total}] ✗ {file_path.name}: {e}", "error")

        except DatabaseError as e:
            self.update_status(f"Database error: {e}", "error")
            return

        # Clear selections after ingestion
        self.selected_files.clear()

        # Final summary
        summary_parts = []
        if inserted > 0:
            summary_parts.append(f"{inserted} new")
        if updated > 0:
            summary_parts.append(f"{updated} updated")
        if duplicates > 0:
            summary_parts.append(f"{duplicates} duplicates")
        if errors > 0:
            summary_parts.append(f"{errors} errors")

        summary = "Complete: " + ", ".join(summary_parts) if summary_parts else "Complete"
        style = "success" if errors == 0 else "warning"
        self.update_status(summary, style)

    def update_status(self, message: str = None, style: str = ""):
        """Update the status bar."""
        if message is None:
            count = len(self.selected_files)
            message = f"Selected: {count} file(s)"

        status = self.query_one("#status", Static)
        status.update(message)

        # Update style
        status.remove_class("success", "error", "warning")
        if style:
            status.add_class(style)


if __name__ == '__main__':
    # For testing
    from src.config import DatabaseConfig
    config = DatabaseConfig()
    app = GrailFileBrowser(config)
    app.run()
