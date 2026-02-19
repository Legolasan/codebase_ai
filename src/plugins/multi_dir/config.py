"""Configuration persistence for multi-directory plugin.

Stores directory configuration in ~/.assistant/directories.json
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default config location
DEFAULT_CONFIG_DIR = Path.home() / ".assistant"
DIRECTORIES_FILE = "directories.json"


@dataclass
class DirectoryConfig:
    """Configuration for a single indexed directory."""

    path: str
    alias: str
    added_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_indexed: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "DirectoryConfig":
        """Create from dictionary."""
        return cls(
            path=data["path"],
            alias=data["alias"],
            added_at=data.get("added_at", datetime.utcnow().isoformat()),
            last_indexed=data.get("last_indexed"),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    def update_indexed(self) -> None:
        """Update the last_indexed timestamp."""
        self.last_indexed = datetime.utcnow().isoformat()


@dataclass
class MultiDirConfig:
    """Configuration for all indexed directories."""

    directories: list[DirectoryConfig] = field(default_factory=list)
    unified_collection: str = "multi_codebase"

    @classmethod
    def from_dict(cls, data: dict) -> "MultiDirConfig":
        """Create from dictionary."""
        return cls(
            directories=[
                DirectoryConfig.from_dict(d) for d in data.get("directories", [])
            ],
            unified_collection=data.get("unified_collection", "multi_codebase"),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "directories": [d.to_dict() for d in self.directories],
            "unified_collection": self.unified_collection,
        }


class DirectoryConfigManager:
    """Manages directory configuration persistence."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or DEFAULT_CONFIG_DIR
        self.config_file = self.config_dir / DIRECTORIES_FILE
        self._config: Optional[MultiDirConfig] = None

    def _ensure_config_dir(self) -> None:
        """Ensure the config directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> MultiDirConfig:
        """Load configuration from file."""
        if self._config is not None:
            return self._config

        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    data = json.load(f)
                self._config = MultiDirConfig.from_dict(data)
                logger.debug(f"Loaded directory config with {len(self._config.directories)} dirs")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load directory config: {e}")
                self._config = MultiDirConfig()
        else:
            self._config = MultiDirConfig()

        return self._config

    def save(self) -> None:
        """Save configuration to file."""
        self._ensure_config_dir()
        config = self.load()

        try:
            with open(self.config_file, "w") as f:
                json.dump(config.to_dict(), f, indent=2)
            logger.debug("Saved directory config")
        except IOError as e:
            logger.error(f"Failed to save directory config: {e}")
            raise

    def add_directory(self, path: str, alias: Optional[str] = None) -> DirectoryConfig:
        """Add a directory to the configuration.

        Args:
            path: Absolute path to the directory
            alias: Optional alias (defaults to directory name)

        Returns:
            The created DirectoryConfig

        Raises:
            ValueError: If path doesn't exist or is already configured
        """
        path_obj = Path(path).resolve()

        if not path_obj.exists():
            raise ValueError(f"Directory does not exist: {path}")

        if not path_obj.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        config = self.load()

        # Check for duplicates
        for existing in config.directories:
            if Path(existing.path).resolve() == path_obj:
                raise ValueError(f"Directory already configured: {path}")

        # Create config with alias defaulting to directory name
        if alias is None:
            alias = path_obj.name

        # Ensure unique alias
        existing_aliases = {d.alias for d in config.directories}
        base_alias = alias
        counter = 1
        while alias in existing_aliases:
            alias = f"{base_alias}_{counter}"
            counter += 1

        dir_config = DirectoryConfig(path=str(path_obj), alias=alias)
        config.directories.append(dir_config)
        self.save()

        logger.info(f"Added directory: {path} as '{alias}'")
        return dir_config

    def remove_directory(self, alias_or_path: str) -> Optional[DirectoryConfig]:
        """Remove a directory from the configuration.

        Args:
            alias_or_path: Either the alias or path of the directory

        Returns:
            The removed DirectoryConfig, or None if not found
        """
        config = self.load()

        for i, dir_config in enumerate(config.directories):
            if dir_config.alias == alias_or_path or dir_config.path == alias_or_path:
                removed = config.directories.pop(i)
                self.save()
                logger.info(f"Removed directory: {removed.path} ('{removed.alias}')")
                return removed

        return None

    def get_directory(self, alias_or_path: str) -> Optional[DirectoryConfig]:
        """Get a directory config by alias or path.

        Args:
            alias_or_path: Either the alias or path of the directory

        Returns:
            DirectoryConfig if found, None otherwise
        """
        config = self.load()

        for dir_config in config.directories:
            if dir_config.alias == alias_or_path or dir_config.path == alias_or_path:
                return dir_config

        return None

    def list_directories(self) -> list[DirectoryConfig]:
        """Get all configured directories."""
        return self.load().directories

    def update_indexed(self, alias_or_path: str) -> None:
        """Update the last_indexed timestamp for a directory.

        Args:
            alias_or_path: Either the alias or path of the directory
        """
        dir_config = self.get_directory(alias_or_path)
        if dir_config:
            dir_config.update_indexed()
            self.save()

    def get_unified_collection(self) -> str:
        """Get the name of the unified collection."""
        return self.load().unified_collection

    def set_unified_collection(self, name: str) -> None:
        """Set the name of the unified collection."""
        config = self.load()
        config.unified_collection = name
        self.save()

    def clear(self) -> None:
        """Clear all directory configuration."""
        self._config = MultiDirConfig()
        self.save()
