"""
Configuration loading and validation for database credentials.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any

# Handle tomli import for Python < 3.11
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        print("Error: tomli package is required for Python < 3.11")
        print("Install with: pip install tomli")
        sys.exit(1)


class ConfigError(Exception):
    """Custom exception for configuration errors."""
    pass


class DatabaseConfig:
    """Database configuration loaded from TOML file."""

    def __init__(self, config_path: str = None):
        """
        Load database configuration from TOML file.

        Args:
            config_path: Optional path to config file. If None, uses default location.
        """
        self.config_path = self._get_config_path(config_path)
        self.config = self._load_config()
        self._validate_config()

    def _get_config_path(self, config_path: str = None) -> Path:
        """
        Determine the configuration file path.

        Priority:
        1. Provided config_path argument
        2. GRAIL_DB_CONFIG environment variable
        3. Default: ~/.config/postgres/save-grail-json.toml
        """
        if config_path:
            return Path(config_path).expanduser()

        env_config = os.environ.get('GRAIL_DB_CONFIG')
        if env_config:
            return Path(env_config).expanduser()

        return Path.home() / '.config' / 'postgres' / 'save-grail-json.toml'

    def _load_config(self) -> Dict[str, Any]:
        """Load and parse the TOML configuration file."""
        if not self.config_path.exists():
            raise ConfigError(
                f"Configuration file not found: {self.config_path}\n"
                f"Please create the file with database credentials.\n"
                f"See PRD.md for configuration format."
            )

        try:
            with open(self.config_path, 'rb') as f:
                return tomllib.load(f)
        except Exception as e:
            raise ConfigError(f"Error parsing configuration file: {e}")

    def _validate_config(self):
        """Validate that required configuration fields are present."""
        if 'server' not in self.config:
            raise ConfigError("Missing [server] section in configuration file")

        server = self.config['server']
        required_fields = ['host', 'port', 'user', 'password']

        missing_fields = [field for field in required_fields if field not in server]
        if missing_fields:
            raise ConfigError(
                f"Missing required fields in [server] section: {', '.join(missing_fields)}"
            )

    @property
    def host(self) -> str:
        """Database host."""
        return self.config['server']['host']

    @property
    def port(self) -> int:
        """Database port."""
        return int(self.config['server']['port'])

    @property
    def user(self) -> str:
        """Database user."""
        return self.config['server']['user']

    @property
    def password(self) -> str:
        """Database password."""
        return self.config['server']['password']

    @property
    def database(self) -> str:
        """Database name (defaults to 'grail_files' if not specified)."""
        return self.config['server'].get('database', 'grail_files')

    def get_connection_params(self, database: str = None) -> Dict[str, Any]:
        """
        Get connection parameters for psycopg2.

        Args:
            database: Override database name. If None, uses config value.

        Returns:
            Dictionary of connection parameters for psycopg2.connect()
        """
        return {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'password': self.password,
            'database': database or self.database,
        }
