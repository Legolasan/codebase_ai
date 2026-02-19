"""Memory plugin for persistent user preferences across sessions.

This plugin stores user notes and preferences that persist across
sessions and injects them into agent system prompts.

Features:
- Store user preferences ("I prefer TypeScript")
- Store context ("Working on e-commerce project")
- Store rules ("Always use pytest for testing")
- Auto-inject memories into agent prompts
- Search and manage memories via CLI

Usage:
    # Enable the plugin
    assistant plugins enable memory

    # Add memories
    assistant memory add "I prefer TypeScript over JavaScript"
    assistant memory add "Use pytest for testing" --category rule
    assistant memory add "Working on e-commerce project" --category context

    # List all memories
    assistant memory list

    # Search memories
    assistant memory search "TypeScript"

    # Remove a memory
    assistant memory remove "I prefer TypeScript over JavaScript"

    # Clear all memories
    assistant memory clear

    # Check status
    assistant memory status
"""

from .manager import Memory, MemoriesManager
from .plugin import MemoryPlugin

__all__ = ["MemoryPlugin", "Memory", "MemoriesManager"]
