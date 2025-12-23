"""
JSON file ingestion and field extraction.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class IngestionError(Exception):
    """Custom exception for ingestion errors."""
    pass


class GrailFileData:
    """Container for extracted grail file data."""

    def __init__(
        self,
        file_path: str,
        json_content: str,
        ticker: Optional[str] = None,
        asset_type: Optional[str] = None,
        file_created_at: Optional[datetime] = None,
        file_modified_at: Optional[datetime] = None
    ):
        self.file_path = file_path
        self.json_content = json_content
        self.ticker = ticker
        self.asset_type = asset_type
        self.file_created_at = file_created_at
        self.file_modified_at = file_modified_at


def ingest_json_file(file_path: str) -> GrailFileData:
    """
    Read and process a JSON file for ingestion.

    Args:
        file_path: Path to the JSON file

    Returns:
        GrailFileData object with extracted information

    Raises:
        IngestionError: If file cannot be read or parsed
    """
    path = Path(file_path)

    # Verify file exists
    if not path.exists():
        raise IngestionError(f"File not found: {file_path}")

    if not path.is_file():
        raise IngestionError(f"Not a file: {file_path}")

    # Read file content
    try:
        with open(path, 'r', encoding='utf-8') as f:
            json_content = f.read()
    except Exception as e:
        raise IngestionError(f"Failed to read file {file_path}: {e}")

    # Parse JSON to extract fields
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError as e:
        raise IngestionError(f"Invalid JSON in {file_path}: {e}")

    # Extract ticker and asset_type (if present)
    ticker = data.get('ticker')
    asset_type = data.get('asset_type')

    # Get file timestamps
    try:
        stat = path.stat()
        # Use birth time if available (creation time), otherwise use ctime
        file_created_at = datetime.fromtimestamp(
            getattr(stat, 'st_birthtime', stat.st_ctime)
        )
        file_modified_at = datetime.fromtimestamp(stat.st_mtime)
    except Exception as e:
        # If we can't get timestamps, continue without them
        file_created_at = None
        file_modified_at = None

    return GrailFileData(
        file_path=str(path.absolute()),
        json_content=json_content,
        ticker=ticker,
        asset_type=asset_type,
        file_created_at=file_created_at,
        file_modified_at=file_modified_at
    )


def validate_json_file(file_path: str) -> bool:
    """
    Check if a file is a valid JSON file without full ingestion.

    Args:
        file_path: Path to check

    Returns:
        True if file exists and contains valid JSON
    """
    path = Path(file_path)

    if not path.exists() or not path.is_file():
        return False

    try:
        with open(path, 'r', encoding='utf-8') as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, Exception):
        return False
