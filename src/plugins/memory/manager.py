"""Memory persistence manager.

Handles storage and retrieval of user memories from ~/.assistant/memories.json.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import uuid


@dataclass
class Memory:
    """A single user memory/preference."""

    id: str
    text: str
    category: str = "preference"  # preference, context, rule
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    tags: list[str] = field(default_factory=list)


class MemoriesManager:
    """Manages memory persistence to ~/.assistant/memories.json."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".assistant"
        self.config_file = self.config_dir / "memories.json"
        self._memories: list[Memory] = []

    def load(self) -> list[Memory]:
        """Load memories from disk."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    data = json.load(f)
                self._memories = [Memory(**m) for m in data.get("memories", [])]
            except (json.JSONDecodeError, TypeError) as e:
                # Handle corrupted file gracefully
                self._memories = []
        else:
            self._memories = []
        return self._memories

    def save(self) -> None:
        """Persist memories to disk."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        data = {"memories": [asdict(m) for m in self._memories], "version": 1}
        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=2)

    def add(self, text: str, category: str = "preference", tags: list[str] = None) -> Memory:
        """Add a new memory.

        Args:
            text: The memory text to store
            category: Category type (preference, context, rule)
            tags: Optional list of tags

        Returns:
            The created Memory object
        """
        memory = Memory(
            id=str(uuid.uuid4()),
            text=text,
            category=category,
            tags=tags or [],
        )
        self._memories.append(memory)
        self.save()
        return memory

    def remove(self, text: str) -> bool:
        """Remove memory by exact text match.

        Args:
            text: The exact memory text to remove

        Returns:
            True if removed, False if not found
        """
        for i, m in enumerate(self._memories):
            if m.text == text:
                self._memories.pop(i)
                self.save()
                return True
        return False

    def remove_by_id(self, memory_id: str) -> bool:
        """Remove memory by ID.

        Args:
            memory_id: The UUID of the memory to remove

        Returns:
            True if removed, False if not found
        """
        for i, m in enumerate(self._memories):
            if m.id == memory_id:
                self._memories.pop(i)
                self.save()
                return True
        return False

    def search(self, query: str) -> list[Memory]:
        """Search memories by keyword (case-insensitive).

        Args:
            query: Search keyword

        Returns:
            List of matching memories
        """
        query_lower = query.lower()
        return [m for m in self._memories if query_lower in m.text.lower()]

    def get_all(self) -> list[Memory]:
        """Get all memories.

        Returns:
            Copy of the memories list
        """
        return self._memories.copy()

    def clear(self) -> int:
        """Clear all memories.

        Returns:
            Count of removed memories
        """
        count = len(self._memories)
        self._memories = []
        self.save()
        return count

    def get_by_category(self, category: str) -> list[Memory]:
        """Get memories by category.

        Args:
            category: The category to filter by

        Returns:
            List of memories in that category
        """
        return [m for m in self._memories if m.category == category]
