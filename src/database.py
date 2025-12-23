"""
Database operations for PostgreSQL storage.
"""

from datetime import datetime
from typing import Optional, Dict, Any
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from src.config import DatabaseConfig


class DatabaseError(Exception):
    """Custom exception for database errors."""
    pass


class GrailDatabase:
    """Manage PostgreSQL database operations for grail JSON files."""

    def __init__(self, config: DatabaseConfig, database_name: str = None):
        """
        Initialize database manager.

        Args:
            config: DatabaseConfig instance with connection parameters
            database_name: Override database name from config
        """
        self.config = config
        self.database_name = database_name or config.database
        self.conn = None
        self.cursor = None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def connect(self):
        """Establish connection to PostgreSQL database."""
        try:
            # First, ensure database exists
            self._ensure_database_exists()

            # Connect to the target database
            params = self.config.get_connection_params(self.database_name)
            self.conn = psycopg2.connect(**params)
            self.cursor = self.conn.cursor()

            # Ensure table schema exists
            self._ensure_schema_exists()

        except psycopg2.Error as e:
            raise DatabaseError(f"Failed to connect to database: {e}")

    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    def _ensure_database_exists(self):
        """Create database if it doesn't exist."""
        # Connect to default 'postgres' database to create our database
        params = self.config.get_connection_params('postgres')

        try:
            conn = psycopg2.connect(**params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.database_name,)
            )

            if not cursor.fetchone():
                # Create database
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(self.database_name)
                    )
                )

            cursor.close()
            conn.close()

        except psycopg2.Error as e:
            raise DatabaseError(f"Failed to create database '{self.database_name}': {e}")

    def _ensure_schema_exists(self):
        """Create table schema if it doesn't exist."""
        schema_sql = """
        CREATE TABLE IF NOT EXISTS grail_files (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(20),
            asset_type VARCHAR(50),
            file_path TEXT NOT NULL UNIQUE,
            file_created_at TIMESTAMP,
            file_modified_at TIMESTAMP,
            json_content TEXT NOT NULL,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_ticker ON grail_files(ticker);
        CREATE INDEX IF NOT EXISTS idx_asset_type ON grail_files(asset_type);
        CREATE INDEX IF NOT EXISTS idx_ingested_at ON grail_files(ingested_at);
        """

        try:
            self.cursor.execute(schema_sql)
            self.conn.commit()
        except psycopg2.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to create table schema: {e}")

    def insert_grail_file(
        self,
        file_path: str,
        json_content: str,
        ticker: Optional[str] = None,
        asset_type: Optional[str] = None,
        file_created_at: Optional[datetime] = None,
        file_modified_at: Optional[datetime] = None
    ) -> bool:
        """
        Insert a grail JSON file into the database.

        Args:
            file_path: Path to the JSON file
            json_content: Complete JSON content as string
            ticker: Ticker symbol extracted from JSON
            asset_type: Asset type extracted from JSON
            file_created_at: File creation timestamp
            file_modified_at: File modification timestamp

        Returns:
            True if inserted successfully, False if duplicate (already exists)

        Raises:
            DatabaseError: If database operation fails (non-duplicate error)
        """
        insert_sql = """
        INSERT INTO grail_files (
            ticker, asset_type, file_path,
            file_created_at, file_modified_at, json_content
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """

        try:
            self.cursor.execute(
                insert_sql,
                (ticker, asset_type, file_path, file_created_at, file_modified_at, json_content)
            )
            self.conn.commit()
            return True

        except psycopg2.IntegrityError as e:
            # Duplicate file_path (UNIQUE constraint violation)
            self.conn.rollback()
            if 'unique constraint' in str(e).lower():
                return False
            raise DatabaseError(f"Database integrity error: {e}")

        except psycopg2.Error as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to insert file: {e}")

    def get_file_count(self) -> int:
        """Get total number of files in database."""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM grail_files")
            return self.cursor.fetchone()[0]
        except psycopg2.Error as e:
            raise DatabaseError(f"Failed to get file count: {e}")

    def file_exists(self, file_path: str) -> bool:
        """Check if a file path already exists in database."""
        try:
            self.cursor.execute(
                "SELECT 1 FROM grail_files WHERE file_path = %s",
                (file_path,)
            )
            return self.cursor.fetchone() is not None
        except psycopg2.Error as e:
            raise DatabaseError(f"Failed to check file existence: {e}")
