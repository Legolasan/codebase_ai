"""GitHub authentication plugin.

Provides secure GitHub authentication with multiple strategies
and enhanced git/GitHub operations.
"""

import getpass
import logging
from typing import Any, Callable, Optional

# Try to import langchain tools (may not be installed)
try:
    from langchain_core.tools import BaseTool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseTool = object

from ..base import BasePlugin, PluginError
from .auth import AuthResult, GitHubAuth
from . import keyring_store
from .tools import create_git_tools

logger = logging.getLogger(__name__)


class GitHubAuthPlugin(BasePlugin):
    """Plugin for GitHub authentication and operations.

    Features:
    - Multiple auth strategies (env, keyring, gh CLI)
    - Secure token storage in system keyring
    - Enhanced git operations (clone, push, pull)
    - GitHub API tools (PRs, issues)

    CLI Commands:
    - auth github --set: Store token
    - auth github --status: Show auth status
    - auth github --remove: Remove token
    - auth github --test: Test authentication
    """

    name = "github_auth"
    description = "GitHub authentication and enhanced git operations"
    version = "1.0.0"
    dependencies = ["httpx"]  # keyring is optional

    def __init__(self):
        super().__init__()
        self.auth = GitHubAuth()
        self._tools = None

    def setup(self) -> None:
        """Initialize the plugin."""
        # Check authentication status on startup
        status = self.auth.get_auth_status()
        if status["authenticated"]:
            logger.info(
                f"GitHub authenticated as {status['username']} "
                f"via {status['method']}"
            )
        else:
            logger.info("GitHub not authenticated (use 'assistant auth github --set')")

    def teardown(self) -> None:
        """Cleanup the plugin."""
        self._tools = None

    def is_available(self) -> bool:
        """Check if dependencies are available."""
        # httpx is required
        try:
            import httpx
            return True
        except ImportError:
            return False

    def get_tools(self) -> list:
        """Return enhanced git/GitHub tools."""
        if not LANGCHAIN_AVAILABLE:
            return []
        if self._tools is None:
            self._tools = create_git_tools(self.auth)
        return self._tools

    def get_commands(self) -> list[Callable]:
        """Return CLI commands for auth management."""
        return [
            self.auth_command,
        ]

    def auth_command(
        self,
        set_token: bool = False,
        status: bool = False,
        remove: bool = False,
        test: bool = False,
    ) -> None:
        """Manage GitHub authentication.

        This is registered as 'assistant auth github'.

        Args:
            set_token: Store a new token
            status: Show current auth status
            remove: Remove stored token
            test: Test current authentication
        """
        from rich.console import Console
        from rich.table import Table
        console = Console()

        if set_token:
            self._handle_set_token(console)
        elif status:
            self._handle_status(console)
        elif remove:
            self._handle_remove(console)
        elif test:
            self._handle_test(console)
        else:
            # Default to showing status
            self._handle_status(console)

    def _handle_set_token(self, console) -> None:
        """Handle storing a new token."""
        # Check if keyring is available
        if not keyring_store.is_available():
            console.print(
                "[yellow]Warning:[/yellow] keyring not installed. "
                "Token will not be stored securely."
            )
            console.print("Install with: pip install keyring")
            console.print("\nAlternatively, set GITHUB_TOKEN environment variable.")
            return

        console.print("[bold]Store GitHub Token[/bold]")
        console.print("Generate a token at: https://github.com/settings/tokens")
        console.print("Required scopes: repo, read:user\n")

        # Securely prompt for token
        token = getpass.getpass("Enter your GitHub token: ")

        if not token:
            console.print("[red]No token provided.[/red]")
            return

        try:
            keyring_store.store_token(token)
            console.print("[green]Token stored securely in system keyring.[/green]")

            # Verify the token
            self._handle_test(console)
        except Exception as e:
            console.print(f"[red]Failed to store token:[/red] {e}")

    def _handle_status(self, console) -> None:
        """Handle showing auth status."""
        status = self.auth.get_auth_status()

        console.print("\n[bold]GitHub Authentication Status[/bold]\n")

        if status["authenticated"]:
            console.print(f"[green]Authenticated:[/green] Yes")
            console.print(f"[green]Username:[/green] {status['username']}")
            console.print(f"[green]Method:[/green] {status['method']}")
        else:
            console.print("[yellow]Authenticated:[/yellow] No")

        # Show strategy status
        console.print("\n[bold]Authentication Sources[/bold]")
        table = Table()
        table.add_column("Strategy", style="cyan")
        table.add_column("Available")
        table.add_column("Has Token")

        for name, info in status["strategies"].items():
            available = "[green]Yes[/green]" if info["available"] else "[dim]No[/dim]"
            has_token = "[green]Yes[/green]" if info["has_token"] else "[dim]No[/dim]"
            table.add_row(name, available, has_token)

        console.print(table)

        # Show keyring info
        keyring_info = keyring_store.get_keyring_info()
        if keyring_info["available"]:
            console.print(
                f"\n[dim]Keyring backend: {keyring_info['backend']}[/dim]"
            )

    def _handle_remove(self, console) -> None:
        """Handle removing stored token."""
        if not keyring_store.has_token():
            console.print("[yellow]No token stored in keyring.[/yellow]")
            return

        # Confirm removal
        confirm = input("Remove stored token? (y/N): ")
        if confirm.lower() != "y":
            console.print("Cancelled.")
            return

        if keyring_store.delete_token():
            console.print("[green]Token removed from keyring.[/green]")
        else:
            console.print("[red]Failed to remove token.[/red]")

    def _handle_test(self, console) -> None:
        """Handle testing authentication."""
        console.print("Testing GitHub authentication...")

        result = self.auth.authenticate()

        if result.success:
            console.print(f"[green]Success![/green] Authenticated as {result.username}")
            console.print(f"[dim]Method: {result.method}[/dim]")
        else:
            console.print(f"[red]Failed:[/red] {result.error}")
            console.print("\nTo authenticate, either:")
            console.print("  1. Run: assistant auth github --set")
            console.print("  2. Set GITHUB_TOKEN environment variable")
            console.print("  3. Run: gh auth login")

    def get_auth(self) -> GitHubAuth:
        """Get the GitHubAuth instance.

        Useful for other plugins that need GitHub authentication.
        """
        return self.auth

    def is_authenticated(self) -> bool:
        """Check if currently authenticated.

        Returns:
            True if a valid token is available
        """
        return self.auth.authenticate().success

    def get_config_schema(self) -> dict[str, Any]:
        """Return configuration schema."""
        return {
            "type": "object",
            "properties": {
                "default_remote": {
                    "type": "string",
                    "description": "Default git remote name",
                    "default": "origin",
                },
                "auto_push": {
                    "type": "boolean",
                    "description": "Automatically push after commits",
                    "default": False,
                },
            },
        }

    def configure(self, config: dict[str, Any]) -> None:
        """Apply configuration."""
        # Store config for use in tools
        self._config = config
