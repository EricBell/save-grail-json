"""
Terminal User Interface for interactive file browsing and selection.
"""

import os
from pathlib import Path
from typing import List, Set

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, DirectoryTree, Static, Button, Input
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
        height: 5;
        background: $panel;
        border: solid $primary;
        padding: 0 1;
    }

    #path-input-container {
        height: 3;
        background: $panel;
        border: solid $primary;
        padding: 0 1;
        layout: horizontal;
    }

    #path-label {
        width: 10;
        content-align: left middle;
    }

    #path-input {
        width: 1fr;
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
        Binding("h", "go_home", "Go to Home"),
        Binding("r", "go_root", "Go to Root"),
        ("escape", "quit", "Quit"),
    ]

    def __init__(self, db_config: DatabaseConfig, database_name: str = None, start_path: str = None):
        super().__init__()
        self.db_config = db_config
        self.database_name = database_name
        self.selected_files: Set[Path] = set()
        self.title = "Save Grail JSON - File Browser"
        self.start_path = start_path or os.getcwd()

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Container(
            Static(
                "↑/↓: Navigate | Enter: Expand/collapse | Space: Select JSON | i: Ingest | h: Home | r: Root | q: Quit",
                id="info-panel"
            ),
            Container(
                Horizontal(
                    Static("Path:", id="path-label"),
                    Input(value=self.start_path, placeholder="Enter path...", id="path-input"),
                    id="path-input-container"
                ),
            ),
            Container(
                DirectoryTree(self.start_path, id="file-tree"),
                id="tree-container"
            ),
            Container(
                Button("Ingest Selected (i)", id="ingest-btn", variant="primary"),
                Button("Home (h)", id="home-btn", variant="default"),
                Button("Root (r)", id="root-btn", variant="default"),
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
        elif event.button.id == "home-btn":
            self.action_go_home()
        elif event.button.id == "root-btn":
            self.action_go_root()
        elif event.button.id == "quit-btn":
            self.action_quit()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle path input submission."""
        if event.input.id == "path-input":
            new_path = event.value.strip()
            if new_path:
                self.change_directory(new_path)

    def action_go_home(self) -> None:
        """Navigate to home directory."""
        home_path = str(Path.home())
        self.change_directory(home_path)

    def action_go_root(self) -> None:
        """Navigate to root directory."""
        self.change_directory("/")

    def change_directory(self, path: str) -> None:
        """
        Change the directory tree to a new path.

        Args:
            path: Path to navigate to
        """
        path_obj = Path(path).expanduser().resolve()

        if not path_obj.exists():
            self.update_status(f"Path does not exist: {path}", "error")
            return

        if not path_obj.is_dir():
            self.update_status(f"Not a directory: {path}", "error")
            return

        # Remove old tree and create new one
        try:
            old_tree = self.query_one("#file-tree", DirectoryTree)
            old_tree.remove()

            # Create new tree with new path
            new_tree = DirectoryTree(str(path_obj), id="file-tree")
            tree_container = self.query_one("#tree-container")
            tree_container.mount(new_tree)

            # Update path input
            path_input = self.query_one("#path-input", Input)
            path_input.value = str(path_obj)

            self.update_status(f"Changed to: {path_obj}")

        except Exception as e:
            self.update_status(f"Error changing directory: {e}", "error")

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
