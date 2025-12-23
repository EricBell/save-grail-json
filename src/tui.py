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
        ("escape", "quit", "Quit"),
    ]

    def __init__(self, db_config: DatabaseConfig, database_name: str = None):
        super().__init__()
        self.db_config = db_config
        self.database_name = database_name
        self.selected_files: Set[Path] = set()
        self.title = "Save Grail JSON - File Browser"

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Container(
            Static(
                "Navigate with arrow keys. Press Space to select/deselect JSON files. Press 'i' to ingest.",
                id="info-panel"
            ),
            Container(
                DirectoryTree(os.getcwd(), id="file-tree"),
                id="tree-container"
            ),
            Container(
                Button("Ingest Selected (i)", id="ingest-btn", variant="primary"),
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
        elif event.button.id == "quit-btn":
            self.action_quit()

    def action_ingest(self) -> None:
        """Ingest all selected files."""
        if not self.selected_files:
            self.update_status("No files selected. Navigate and press Space to select JSON files.", "warning")
            return

        files = list(self.selected_files)
        total = len(files)
        success = 0
        errors = 0
        duplicates = 0

        self.update_status(f"Ingesting {total} file(s)...", "")

        try:
            with GrailDatabase(self.db_config, self.database_name) as db:
                for i, file_path in enumerate(files, 1):
                    try:
                        # Ingest the file
                        file_data = ingest_json_file(str(file_path))

                        # Insert into database
                        inserted = db.insert_grail_file(
                            file_path=file_data.file_path,
                            json_content=file_data.json_content,
                            ticker=file_data.ticker,
                            asset_type=file_data.asset_type,
                            file_created_at=file_data.file_created_at,
                            file_modified_at=file_data.file_modified_at
                        )

                        if inserted:
                            success += 1
                            self.update_status(f"[{i}/{total}] ✓ {file_path.name}", "success")
                        else:
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
        summary = f"Complete: {success} ingested"
        if duplicates > 0:
            summary += f", {duplicates} duplicates"
        if errors > 0:
            summary += f", {errors} errors"

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
