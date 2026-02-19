"""Context7 MCP integration plugin.

Provides deep research capabilities for competitor analysis
and up-to-date library documentation via Context7's MCP server.
"""

import asyncio
import logging
from typing import Any, Callable, Optional

# Try to import langchain tools (may not be installed)
try:
    from langchain_core.tools import BaseTool, tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseTool = object
    def tool(func):
        return func

from ..base import BasePlugin, PluginError
from .mcp_client import Context7Client, check_context7_available

logger = logging.getLogger(__name__)


class Context7Plugin(BasePlugin):
    """Plugin for Context7 MCP integration.

    Features:
    - Up-to-date library documentation lookup
    - Competitor research for PRD generation
    - Multi-library topic research

    Requires:
    - CONTEXT7_API_KEY environment variable
    - Optional: langchain-mcp-adapters for full MCP support

    CLI Commands:
    - context7 status: Show Context7 configuration
    - context7 lookup <library>: Look up library docs
    """

    name = "context7"
    description = "Deep research via Context7 MCP for competitor analysis"
    version = "1.0.0"
    dependencies = ["httpx"]  # MCP adapters are optional

    def __init__(self):
        super().__init__()
        self.client = Context7Client()
        self._connected = False

    def setup(self) -> None:
        """Initialize the plugin and connect to Context7."""
        if not self.client.is_configured:
            logger.warning(
                "Context7 API key not set. "
                "Set CONTEXT7_API_KEY environment variable."
            )
            return

        # Try to connect asynchronously
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, schedule the connection
                asyncio.create_task(self._async_setup())
            else:
                loop.run_until_complete(self._async_setup())
        except RuntimeError:
            # No event loop, create one
            asyncio.run(self._async_setup())

    async def _async_setup(self) -> None:
        """Async setup to connect to Context7."""
        self._connected = await self.client.connect()
        if self._connected:
            logger.info("Connected to Context7")
        else:
            logger.warning("Failed to connect to Context7")

    def teardown(self) -> None:
        """Disconnect from Context7."""
        if self._connected:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.client.disconnect())
                else:
                    loop.run_until_complete(self.client.disconnect())
            except Exception:
                pass
            self._connected = False

    def is_available(self) -> bool:
        """Check if Context7 is available."""
        try:
            import httpx
            return self.client.is_configured
        except ImportError:
            return False

    def get_tools(self) -> list:
        """Return Context7 research tools."""
        if not LANGCHAIN_AVAILABLE:
            return []
        return [
            self._create_research_competitor_tool(),
            self._create_get_library_docs_tool(),
            self._create_compare_libraries_tool(),
        ]

    def get_commands(self) -> list[Callable]:
        """Return CLI commands."""
        return [
            self.context7_command,
        ]

    def _create_research_competitor_tool(self):
        """Create tool for competitor research."""
        plugin = self

        @tool
        def research_competitor(
            competitor_name: str,
            feature: Optional[str] = None,
        ) -> str:
            """Research competitor library documentation for feature parity analysis.

            Use this when creating PRDs to understand how competitors implement features.

            Args:
                competitor_name: Name of the competitor library/product
                feature: Specific feature to research (optional)

            Returns:
                Documentation and analysis of competitor's implementation
            """
            return asyncio.run(
                plugin._research_competitor_async(competitor_name, feature)
            )

        return research_competitor

    def _create_get_library_docs_tool(self):
        """Create tool for library documentation lookup."""
        plugin = self

        @tool
        def get_library_docs(
            library: str,
            topic: Optional[str] = None,
        ) -> str:
            """Get up-to-date documentation for a library.

            Args:
                library: Library name (e.g., "react", "fastapi", "langchain")
                topic: Specific topic to look up (optional)

            Returns:
                Library documentation content
            """
            return asyncio.run(
                plugin._get_library_docs_async(library, topic)
            )

        return get_library_docs

    def _create_compare_libraries_tool(self):
        """Create tool for comparing libraries."""
        plugin = self

        @tool
        def compare_libraries(
            libraries: str,
            feature: str,
        ) -> str:
            """Compare how different libraries implement a feature.

            Args:
                libraries: Comma-separated list of library names
                feature: Feature to compare

            Returns:
                Comparison analysis
            """
            lib_list = [lib.strip() for lib in libraries.split(",")]
            return asyncio.run(
                plugin._compare_libraries_async(lib_list, feature)
            )

        return compare_libraries

    async def _research_competitor_async(
        self,
        competitor_name: str,
        feature: Optional[str] = None,
    ) -> str:
        """Async implementation of competitor research."""
        if not self._connected:
            await self.client.connect()

        # Resolve the library
        lib_info = await self.client.resolve_library(competitor_name)
        if not lib_info:
            return f"Could not find library: {competitor_name}"

        # Get documentation
        docs = await self.client.get_documentation(
            lib_info.library_id,
            topic=feature,
            max_tokens=5000,
        )

        if not docs:
            return f"No documentation found for {competitor_name}"

        # Format response
        lines = [
            f"## {lib_info.name}",
            "",
            f"**Description:** {lib_info.description}",
        ]

        if lib_info.version:
            lines.append(f"**Version:** {lib_info.version}")

        if feature:
            lines.append(f"\n### Feature: {feature}")

        lines.append("")
        lines.append(docs.content)

        if docs.source_url:
            lines.append(f"\n_Source: {docs.source_url}_")

        return "\n".join(lines)

    async def _get_library_docs_async(
        self,
        library: str,
        topic: Optional[str] = None,
    ) -> str:
        """Async implementation of library docs lookup."""
        if not self._connected:
            await self.client.connect()

        # Resolve the library
        lib_info = await self.client.resolve_library(library)
        if not lib_info:
            return f"Could not find library: {library}"

        # Get documentation
        docs = await self.client.get_documentation(
            lib_info.library_id,
            topic=topic,
            max_tokens=5000,
        )

        if not docs:
            return f"No documentation found for {library}"

        # Format response
        lines = [f"## {lib_info.name} Documentation"]

        if topic:
            lines.append(f"\n### Topic: {topic}")

        lines.append("")
        lines.append(docs.content)

        return "\n".join(lines)

    async def _compare_libraries_async(
        self,
        libraries: list[str],
        feature: str,
    ) -> str:
        """Async implementation of library comparison."""
        if not self._connected:
            await self.client.connect()

        results = await self.client.research_topic(feature, libraries)

        if not results:
            return f"No documentation found for: {', '.join(libraries)}"

        # Format comparison
        lines = [
            f"## Feature Comparison: {feature}",
            "",
        ]

        for result in results:
            lines.append(f"### {result.library_id}")
            lines.append("")
            lines.append(result.content[:2000])  # Limit per library
            if len(result.content) > 2000:
                lines.append("... (truncated)")
            lines.append("")

        return "\n".join(lines)

    def context7_command(
        self,
        status: bool = False,
        lookup: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> None:
        """Context7 CLI commands.

        Args:
            status: Show Context7 configuration status
            lookup: Look up a library's documentation
            topic: Topic to search for (with --lookup)
        """
        from rich.console import Console
        from rich.table import Table
        console = Console()

        if lookup:
            self._handle_lookup(console, lookup, topic)
        elif status or (not lookup):
            self._handle_status(console)

    def _handle_status(self, console) -> None:
        """Handle status command."""
        status = check_context7_available()

        console.print("\n[bold]Context7 Status[/bold]\n")

        table = Table()
        table.add_column("Component", style="cyan")
        table.add_column("Status")

        table.add_row(
            "API Key",
            "[green]Set[/green]" if status["api_key_set"] else "[red]Not set[/red]"
        )
        table.add_row(
            "MCP Adapters",
            "[green]Installed[/green]" if status["mcp_available"] else "[yellow]Not installed[/yellow]"
        )
        table.add_row(
            "npx (for MCP)",
            "[green]Available[/green]" if status["npx_available"] else "[yellow]Not found[/yellow]"
        )
        table.add_row(
            "Connected",
            "[green]Yes[/green]" if self._connected else "[yellow]No[/yellow]"
        )

        console.print(table)

        if not status["api_key_set"]:
            console.print("\n[yellow]Set CONTEXT7_API_KEY to enable Context7.[/yellow]")

        if not status["mcp_available"]:
            console.print(
                "\n[dim]Install langchain-mcp-adapters for full MCP support:[/dim]"
            )
            console.print("  pip install langchain-mcp-adapters")

    def _handle_lookup(self, console, library: str, topic: Optional[str]) -> None:
        """Handle library lookup command."""
        console.print(f"Looking up {library}...")

        try:
            result = asyncio.run(self._get_library_docs_async(library, topic))
            console.print(result)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")

    def get_config_schema(self) -> dict[str, Any]:
        """Return configuration schema."""
        return {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "Context7 API key (alternative to env var)",
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum tokens per documentation request",
                    "default": 5000,
                },
                "use_for": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Which agents can use Context7",
                    "default": ["prd_research"],
                },
            },
        }

    def configure(self, config: dict[str, Any]) -> None:
        """Apply configuration."""
        if "api_key" in config:
            self.client = Context7Client(api_key=config["api_key"])
