"""Memory plugin for persistent user preferences across sessions.

Stores user notes that persist across sessions and injects
them into agent system prompts.
"""

import logging
from typing import Any, Callable, Optional

from ..base import BasePlugin
from .manager import MemoriesManager, Memory

logger = logging.getLogger(__name__)


class MemoryPlugin(BasePlugin):
    """Persistent user memories and preferences.

    Stores user notes that persist across sessions and injects
    them into agent system prompts so the assistant "remembers"
    user preferences.

    Configuration (in ~/.assistant/plugins.json):
    ```json
    {
      "memory": {
        "max_memories": 50,
        "inject_limit": 10
      }
    }
    ```

    Usage:
        assistant memory add "I prefer TypeScript"
        assistant memory add "Use pytest" --category rule
        assistant memory list
        assistant memory search "TypeScript"
        assistant memory remove "I prefer TypeScript"
        assistant memory clear
        assistant memory status
    """

    name = "memory"
    description = "Persistent user memories and preferences across sessions"
    version = "1.0.0"
    dependencies = []

    def __init__(self):
        super().__init__()
        self.manager = MemoriesManager()
        self.max_memories = 50
        self.inject_limit = 10  # Max memories to inject into prompts

    def configure(self, config: dict[str, Any]) -> None:
        """Apply configuration from plugins.json.

        Args:
            config: Configuration dict with optional keys:
                - max_memories: Maximum memories to store (default: 50)
                - inject_limit: Max memories to inject into prompts (default: 10)
        """
        if "max_memories" in config:
            self.max_memories = config["max_memories"]
        if "inject_limit" in config:
            self.inject_limit = config["inject_limit"]

    def setup(self) -> None:
        """Load memories on plugin enable."""
        self.manager.load()
        count = len(self.manager.get_all())
        logger.info(f"Memory plugin initialized with {count} memories")

    def teardown(self) -> None:
        """Save memories on plugin disable."""
        self.manager.save()

    def get_tools(self) -> list:
        """No LangChain tools - CLI only."""
        return []

    def get_commands(self) -> list[Callable]:
        """Return CLI command handlers."""
        return []

    def get_system_prompt_addition(self) -> Optional[str]:
        """Inject memories into agent system prompts.

        Groups memories by category and formats them for inclusion
        in the agent's system prompt.

        Returns:
            Formatted memory prompt string, or None if no memories
        """
        memories = self.manager.get_all()
        if not memories:
            return None

        # Group by category
        by_category: dict[str, list[str]] = {}
        for m in memories[: self.inject_limit]:
            cat = m.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(m.text)

        # Format output
        sections = []
        for category, items in by_category.items():
            section = f"**{category.title()}:**\n" + "\n".join(
                f"- {item}" for item in items
            )
            sections.append(section)

        memories_text = "\n\n".join(sections)

        return f"""[User Memories]
The user has saved these preferences and context. Apply them when relevant:

{memories_text}

Use these memories to personalize responses and respect user preferences."""

    # =========================================================================
    # CLI Command Methods
    # =========================================================================

    def add_memory_command(self, text: str, category: str = "preference") -> None:
        """Add a new memory.

        Args:
            text: The memory text to store
            category: Category type (preference, context, rule)
        """
        from rich.console import Console

        console = Console()

        if len(self.manager.get_all()) >= self.max_memories:
            console.print(
                f"[yellow]Maximum memories ({self.max_memories}) reached. "
                "Remove some first.[/yellow]"
            )
            return

        memory = self.manager.add(text, category)
        console.print(f"[green]Memory added:[/green] {text}")
        console.print(f"[dim]Category: {category} | ID: {memory.id[:8]}[/dim]")

    def list_memories_command(self, category: Optional[str] = None) -> None:
        """List all memories.

        Args:
            category: Optional category to filter by
        """
        from rich.console import Console
        from rich.table import Table

        console = Console()

        memories = self.manager.get_all()
        if category:
            memories = [m for m in memories if m.category == category]

        if not memories:
            console.print("[yellow]No memories stored.[/yellow]")
            console.print('[dim]Add one with: assistant memory add "your note"[/dim]')
            return

        table = Table(title=f"User Memories ({len(memories)})")
        table.add_column("Category", style="cyan", width=12)
        table.add_column("Memory", style="white")
        table.add_column("Created", style="dim", width=12)

        for m in memories:
            table.add_row(m.category, m.text, m.created_at[:10])

        console.print(table)

    def remove_memory_command(self, text: str) -> None:
        """Remove a memory by text.

        Args:
            text: The exact memory text to remove
        """
        from rich.console import Console

        console = Console()

        if self.manager.remove(text):
            console.print(f"[green]Removed:[/green] {text}")
        else:
            console.print(f"[yellow]Not found:[/yellow] {text}")
            console.print("[dim]Use 'assistant memory list' to see all memories[/dim]")

    def search_memories_command(self, query: str) -> None:
        """Search memories by keyword.

        Args:
            query: Search keyword
        """
        from rich.console import Console

        console = Console()

        results = self.manager.search(query)

        if not results:
            console.print(f"[yellow]No memories match:[/yellow] {query}")
            return

        console.print(f"\n[bold]Found {len(results)} memories:[/bold]\n")
        for m in results:
            console.print(f"  [{m.category}] {m.text}")

    def clear_memories_command(self, confirm: bool = False) -> None:
        """Clear all memories.

        Args:
            confirm: If True, skip confirmation prompt
        """
        from rich.console import Console
        from rich.prompt import Confirm

        console = Console()

        if not confirm:
            confirm = Confirm.ask("Are you sure you want to clear all memories?")

        if confirm:
            count = self.manager.clear()
            console.print(f"[green]Cleared {count} memories[/green]")
        else:
            console.print("[dim]Cancelled[/dim]")

    def status_command(self) -> None:
        """Show memory plugin status."""
        from rich.console import Console
        from rich.table import Table

        console = Console()

        memories = self.manager.get_all()

        table = Table(title="Memory Plugin Status")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Memories", str(len(memories)))
        table.add_row("Max Memories", str(self.max_memories))
        table.add_row("Inject Limit", str(self.inject_limit))
        table.add_row("Storage File", str(self.manager.config_file))

        # Count by category
        categories: dict[str, int] = {}
        for m in memories:
            categories[m.category] = categories.get(m.category, 0) + 1

        if categories:
            table.add_row("", "")
            for cat, count in categories.items():
                table.add_row(f"  {cat}", str(count))

        console.print(table)
