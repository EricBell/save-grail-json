#!/usr/bin/env python3
"""
Version management system with file hashing
Automatically tracks file changes and manages version numbers (major.minor.patch format)

Version is stored in pyproject.toml and synced to src/__init__.py
File hashes are tracked separately in .version_hashes.json

To bump up the major version, use:
    python version_manager.py major
To bump up the minor version, use:
    python version_manager.py minor
To bump up the patch version, use:
    python version_manager.py patch
To reset the version to v1.0.0, use:
    python version_manager.py reset
To reset to a specific version, use:
    python version_manager.py reset <major> <minor> <patch>
To check for changes and update the version, use:
    python version_manager.py check
To get the current version, use:
    python version_manager.py status
"""

import os
import json
import hashlib
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple

import tomlkit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VersionManager:
    """Manages application versioning based on file hashes"""

    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent
        self.pyproject_path = self.project_root / 'pyproject.toml'
        self.init_path = self.project_root / 'src' / '__init__.py'
        self.hashes_file = self.project_root / '.version_hashes.json'
        self.tracked_files = [
            'src/**/*.py',
            'pyproject.toml',
        ]

    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Could not hash {file_path}: {e}")
            return ""

    def _get_all_tracked_files(self) -> List[Path]:
        """Get all files matching the tracked patterns"""
        all_files = []

        for pattern in self.tracked_files:
            if '**' in pattern:
                # Recursive glob
                files = list(self.project_root.glob(pattern))
            else:
                # Simple glob
                files = list(self.project_root.glob(pattern))

            # Filter out dist/, build/, __pycache__ directories
            filtered_files = []
            for f in files:
                if f.is_file():
                    rel_path = f.relative_to(self.project_root)
                    if not any(part.startswith('.') or part in ['dist', 'build', '__pycache__', 'instance']
                             for part in rel_path.parts):
                        filtered_files.append(f)

            all_files.extend(filtered_files)

        return sorted(set(all_files))

    def _calculate_file_hashes(self) -> Dict[str, str]:
        """Calculate hashes for all tracked files"""
        hashes = {}
        tracked_files = self._get_all_tracked_files()

        for file_path in tracked_files:
            rel_path = str(file_path.relative_to(self.project_root))
            hashes[rel_path] = self._get_file_hash(file_path)

        return hashes

    def _load_file_hashes(self) -> Dict[str, str]:
        """Load file hashes from .version_hashes.json"""
        if not self.hashes_file.exists():
            return {}

        try:
            with open(self.hashes_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading hashes file: {e}")
            return {}

    def _save_file_hashes(self, hashes: Dict[str, str]) -> None:
        """Save file hashes to .version_hashes.json"""
        try:
            with open(self.hashes_file, 'w') as f:
                json.dump(hashes, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving hashes file: {e}")

    def _read_version_from_pyproject(self) -> Tuple[int, int, int]:
        """Read version from pyproject.toml"""
        if not self.pyproject_path.exists():
            logger.error(f"pyproject.toml not found at {self.pyproject_path}")
            return (0, 1, 0)

        try:
            with open(self.pyproject_path, 'r') as f:
                pyproject = tomlkit.load(f)

            version_str = pyproject.get('project', {}).get('version', '0.1.0')
            # Parse version string like "0.1.0" into (0, 1, 0)
            parts = version_str.split('.')
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 1
            patch = int(parts[2]) if len(parts) > 2 else 0

            return (major, minor, patch)
        except Exception as e:
            logger.error(f"Error reading version from pyproject.toml: {e}")
            return (0, 1, 0)

    def _write_version_to_pyproject(self, major: int, minor: int, patch: int) -> None:
        """Write version to pyproject.toml"""
        try:
            with open(self.pyproject_path, 'r') as f:
                pyproject = tomlkit.load(f)

            # Update version in project section
            if 'project' not in pyproject:
                pyproject['project'] = {}
            pyproject['project']['version'] = f"{major}.{minor}.{patch}"

            with open(self.pyproject_path, 'w') as f:
                tomlkit.dump(pyproject, f)

        except Exception as e:
            logger.error(f"Error writing version to pyproject.toml: {e}")
            raise

    def _write_version_to_init_py(self, major: int, minor: int, patch: int) -> None:
        """Write version to src/__init__.py"""
        try:
            version_str = f'"{major}.{minor}.{patch}"'

            if not self.init_path.exists():
                # Create file if it doesn't exist
                self.init_path.parent.mkdir(parents=True, exist_ok=True)
                content = f'"""\nsave-grail-json: A tool to save grail JSON docs to a database for later review and analysis\n"""\n\n__version__ = {version_str}\n'
                with open(self.init_path, 'w') as f:
                    f.write(content)
            else:
                # Update existing file
                with open(self.init_path, 'r') as f:
                    content = f.read()

                # Replace __version__ = "..." with new version
                pattern = r'__version__\s*=\s*["\'][^"\']*["\']'
                replacement = f'__version__ = {version_str}'

                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                else:
                    # Add __version__ if it doesn't exist
                    content += f'\n__version__ = {version_str}\n'

                with open(self.init_path, 'w') as f:
                    f.write(content)

        except Exception as e:
            logger.error(f"Error writing version to src/__init__.py: {e}")
            raise

    def get_current_version(self) -> Tuple[int, int, int]:
        """Get current version without checking for changes"""
        return self._read_version_from_pyproject()

    def check_and_update_version(self) -> Tuple[int, int, int, bool]:
        """Check for file changes and update version if needed"""
        major, minor, patch = self._read_version_from_pyproject()
        current_hashes = self._calculate_file_hashes()
        previous_hashes = self._load_file_hashes()

        # Check if any files have changed
        files_changed = False
        changed_files = []

        # Check for modified files
        for file_path, current_hash in current_hashes.items():
            if file_path in previous_hashes:
                if previous_hashes[file_path] != current_hash:
                    files_changed = True
                    changed_files.append(f"Modified: {file_path}")
            else:
                files_changed = True
                changed_files.append(f"Added: {file_path}")

        # Check for removed files
        for file_path in previous_hashes:
            if file_path not in current_hashes:
                files_changed = True
                changed_files.append(f"Removed: {file_path}")

        if files_changed:
            # Increment patch version for file changes
            patch += 1
            self._write_version_to_pyproject(major, minor, patch)
            self._write_version_to_init_py(major, minor, patch)
            self._save_file_hashes(current_hashes)

            logger.info(f"Version updated to {major}.{minor}.{patch}")
            for change in changed_files:
                logger.info(f"  {change}")

        return major, minor, patch, files_changed

    def increment_major_version(self) -> Tuple[int, int, int]:
        """Manually increment major version and reset minor/patch to 0"""
        major, minor, patch = self._read_version_from_pyproject()
        major += 1
        minor = 0
        patch = 0

        self._write_version_to_pyproject(major, minor, patch)
        self._write_version_to_init_py(major, minor, patch)
        self._save_file_hashes(self._calculate_file_hashes())

        logger.info(f"Major version incremented to {major}.{minor}.{patch}")
        return major, minor, patch

    def increment_minor_version(self) -> Tuple[int, int, int]:
        """Manually increment minor version and reset patch to 0"""
        major, minor, patch = self._read_version_from_pyproject()
        minor += 1
        patch = 0

        self._write_version_to_pyproject(major, minor, patch)
        self._write_version_to_init_py(major, minor, patch)
        self._save_file_hashes(self._calculate_file_hashes())

        logger.info(f"Minor version incremented to {major}.{minor}.{patch}")
        return major, minor, patch

    def increment_patch_version(self) -> Tuple[int, int, int]:
        """Manually increment patch version"""
        major, minor, patch = self._read_version_from_pyproject()
        patch += 1

        self._write_version_to_pyproject(major, minor, patch)
        self._write_version_to_init_py(major, minor, patch)
        self._save_file_hashes(self._calculate_file_hashes())

        logger.info(f"Patch version incremented to {major}.{minor}.{patch}")
        return major, minor, patch

    def get_version_string(self) -> str:
        """Get formatted version string"""
        major, minor, patch, _ = self.check_and_update_version()
        return f"v{major}.{minor}.{patch}"

    def reset_version(self, major: int = 1, minor: int = 0, patch: int = 0) -> Tuple[int, int, int]:
        """Reset version to specified values"""
        self._write_version_to_pyproject(major, minor, patch)
        self._write_version_to_init_py(major, minor, patch)
        self._save_file_hashes(self._calculate_file_hashes())

        logger.info(f"Version reset to {major}.{minor}.{patch}")
        return major, minor, patch

# Global version manager instance
version_manager = VersionManager()

def get_version_string() -> str:
    """Convenience function to get version string"""
    return version_manager.get_version_string()

def increment_major() -> str:
    """Convenience function to increment major version"""
    major, minor, patch = version_manager.increment_major_version()
    return f"v{major}.{minor}.{patch}"

# CLI interface
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Version Manager Commands:")
        print("  python version_manager.py status      - Show current version")
        print("  python version_manager.py check       - Check for changes and update")
        print("  python version_manager.py major       - Increment major version")
        print("  python version_manager.py minor       - Increment minor version")
        print("  python version_manager.py patch       - Increment patch version")
        print("  python version_manager.py reset       - Reset to v1.0.0")
        print("  python version_manager.py reset X Y Z - Reset to vX.Y.Z")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == 'status':
        major, minor, patch = version_manager.get_current_version()
        print(f"Current version: v{major}.{minor}.{patch}")

    elif command == 'check':
        major, minor, patch, changed = version_manager.check_and_update_version()
        if changed:
            print(f"Version updated to v{major}.{minor}.{patch}")
        else:
            print(f"No changes detected. Version remains v{major}.{minor}.{patch}")

    elif command == 'major':
        major, minor, patch = version_manager.increment_major_version()
        print(f"Major version incremented to v{major}.{minor}.{patch}")

    elif command == 'minor':
        major, minor, patch = version_manager.increment_minor_version()
        print(f"Minor version incremented to v{major}.{minor}.{patch}")

    elif command == 'patch':
        major, minor, patch = version_manager.increment_patch_version()
        print(f"Patch version incremented to v{major}.{minor}.{patch}")

    elif command == 'reset':
        if len(sys.argv) == 5:
            try:
                major = int(sys.argv[2])
                minor = int(sys.argv[3])
                patch = int(sys.argv[4])
                major, minor, patch = version_manager.reset_version(major, minor, patch)
                print(f"Version reset to v{major}.{minor}.{patch}")
            except ValueError:
                print("Error: Major, minor, and patch versions must be integers")
                sys.exit(1)
        else:
            major, minor, patch = version_manager.reset_version()
            print(f"Version reset to v{major}.{minor}.{patch}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
