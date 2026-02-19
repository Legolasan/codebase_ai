"""Multi-directory support plugin.

Allows indexing and searching across multiple codebases with
unified search and source-aware filtering.
"""

import logging
from pathlib import Path
from typing import Any, Callable, Optional, TYPE_CHECKING

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
from .config import DirectoryConfig, DirectoryConfigManager

logger = logging.getLogger(__name__)


class MultiDirPlugin(BasePlugin):
    """Plugin for managing multiple indexed directories.

    Features:
    - Add/remove directories with aliases
    - Unified indexing across all directories
    - Source-aware search filtering
    - Persistent configuration

    CLI Commands:
    - add-dir: Add a directory to index
    - list-dirs: Show configured directories
    - remove-dir: Remove a directory
    - reindex: Re-index all directories
    """

    name = "multi_dir"
    description = "Index and search across multiple codebases"
    version = "1.0.0"
    dependencies = []  # Uses only built-in packages

    def __init__(self):
        super().__init__()
        self.config_manager = DirectoryConfigManager()
        self._vector_store = None

    def setup(self) -> None:
        """Initialize the plugin."""
        # Load configuration
        self.config_manager.load()
        logger.info(f"Multi-dir plugin initialized with {len(self.config_manager.list_directories())} directories")

    def teardown(self) -> None:
        """Cleanup the plugin."""
        self._vector_store = None

    def get_tools(self) -> list:
        """Return LangChain tools for multi-directory operations."""
        if not LANGCHAIN_AVAILABLE:
            return []
        return [
            self._create_search_all_dirs_tool(),
            self._create_list_sources_tool(),
        ]

    def get_commands(self) -> list[Callable]:
        """Return CLI commands for directory management."""
        return [
            self.add_directory_command,
            self.list_directories_command,
            self.remove_directory_command,
            self.reindex_command,
        ]

    def _create_search_all_dirs_tool(self):
        """Create tool for searching across all directories."""
        plugin = self

        @tool
        def search_all_directories(
            query: str,
            n_results: int = 5,
            source_filter: Optional[str] = None,
        ) -> str:
            """Search across all indexed directories.

            Args:
                query: Search query text
                n_results: Number of results to return (default: 5)
                source_filter: Optional source directory alias to filter by

            Returns:
                Formatted search results with source annotations
            """
            return plugin.search(query, n_results, source_filter)

        return search_all_directories

    def _create_list_sources_tool(self):
        """Create tool for listing indexed sources."""
        plugin = self

        @tool
        def list_indexed_sources() -> str:
            """List all indexed directory sources.

            Returns:
                Formatted list of indexed directories with stats
            """
            dirs = plugin.config_manager.list_directories()
            if not dirs:
                return "No directories configured. Use 'assistant add-dir' to add directories."

            lines = ["Indexed directories:"]
            for d in dirs:
                indexed = f" (indexed: {d.last_indexed})" if d.last_indexed else " (not indexed)"
                lines.append(f"  - {d.alias}: {d.path}{indexed}")

            return "\n".join(lines)

        return list_indexed_sources

    def add_directory(self, path: str, alias: Optional[str] = None) -> DirectoryConfig:
        """Add a directory and index it into the unified collection.

        Args:
            path: Path to the directory
            alias: Optional alias for the directory

        Returns:
            The created DirectoryConfig

        Raises:
            PluginError: If adding fails
        """
        try:
            dir_config = self.config_manager.add_directory(path, alias)
            # Index the new directory
            self._index_directory(dir_config)
            return dir_config
        except ValueError as e:
            raise PluginError(self.name, str(e))

    def remove_directory(self, alias_or_path: str) -> bool:
        """Remove a directory and re-index.

        Args:
            alias_or_path: Alias or path of the directory to remove

        Returns:
            True if removed, False if not found
        """
        removed = self.config_manager.remove_directory(alias_or_path)
        if removed:
            # Re-index without the removed directory
            self.reindex_all()
            return True
        return False

    def reindex_all(self) -> dict[str, Any]:
        """Re-index all directories into the unified collection.

        Returns:
            Statistics about the indexing operation
        """
        from indexer.vector_store import VectorStore
        from indexer.file_loader import FileLoader, CodeChunk

        collection_name = self.config_manager.get_unified_collection()
        store = VectorStore(collection_name)

        # Clear existing data
        try:
            store.clear()
        except Exception:
            pass

        # Recreate store
        store = VectorStore(collection_name)

        stats = {
            "directories": 0,
            "total_files": 0,
            "total_chunks": 0,
            "by_source": {},
        }

        for dir_config in self.config_manager.list_directories():
            try:
                dir_stats = self._index_directory_to_store(dir_config, store)
                stats["directories"] += 1
                stats["total_files"] += dir_stats["files"]
                stats["total_chunks"] += dir_stats["chunks"]
                stats["by_source"][dir_config.alias] = dir_stats
                self.config_manager.update_indexed(dir_config.alias)
            except Exception as e:
                logger.error(f"Failed to index {dir_config.path}: {e}")
                stats["by_source"][dir_config.alias] = {"error": str(e)}

        self._vector_store = store
        return stats

    def _index_directory(self, dir_config: DirectoryConfig) -> dict[str, Any]:
        """Index a single directory into the unified collection.

        Args:
            dir_config: Configuration for the directory to index

        Returns:
            Statistics about the indexing
        """
        from indexer.vector_store import VectorStore

        collection_name = self.config_manager.get_unified_collection()

        if self._vector_store is None:
            self._vector_store = VectorStore(collection_name)

        stats = self._index_directory_to_store(dir_config, self._vector_store)
        self.config_manager.update_indexed(dir_config.alias)
        return stats

    def _index_directory_to_store(
        self,
        dir_config: DirectoryConfig,
        store: "VectorStore",
    ) -> dict[str, Any]:
        """Index a directory into a specific store.

        Adds source_dir metadata to each chunk for filtering.
        """
        from indexer.file_loader import FileLoader, CodeChunk
        from dataclasses import dataclass, field

        loader = FileLoader(dir_config.path)

        # Collect chunks with source metadata
        chunks_with_source = []
        for chunk in loader.load_chunks():
            # Create modified chunk with source_dir in metadata
            modified_metadata = {
                **chunk.metadata,
                "source_dir": dir_config.alias,
                "source_path": dir_config.path,
            }

            # Create a wrapper chunk with the modified metadata
            @dataclass
            class SourceChunk:
                content: str
                file_path: str
                start_line: int
                end_line: int
                language: str
                chunk_index: int
                source_dir: str

                @property
                def metadata(self) -> dict:
                    return {
                        "file_path": self.file_path,
                        "start_line": self.start_line,
                        "end_line": self.end_line,
                        "language": self.language,
                        "chunk_index": self.chunk_index,
                        "source_dir": self.source_dir,
                    }

                @property
                def id(self) -> str:
                    return f"{self.source_dir}:{self.file_path}:{self.start_line}-{self.end_line}"

            source_chunk = SourceChunk(
                content=chunk.content,
                file_path=chunk.file_path,
                start_line=chunk.start_line,
                end_line=chunk.end_line,
                language=chunk.language,
                chunk_index=chunk.chunk_index,
                source_dir=dir_config.alias,
            )
            chunks_with_source.append(source_chunk)

        # Add chunks to store
        if chunks_with_source:
            total_added = store.add_chunks(chunks_with_source)
        else:
            total_added = 0

        file_count = len(set(c.file_path for c in chunks_with_source))

        return {
            "files": file_count,
            "chunks": total_added,
            "path": dir_config.path,
        }

    def search(
        self,
        query: str,
        n_results: int = 5,
        source_filter: Optional[str] = None,
    ) -> str:
        """Search across all indexed directories.

        Args:
            query: Search query
            n_results: Number of results
            source_filter: Optional source alias to filter by

        Returns:
            Formatted search results
        """
        from indexer.vector_store import VectorStore

        if self._vector_store is None:
            collection_name = self.config_manager.get_unified_collection()
            self._vector_store = VectorStore(collection_name)

        # Build filter
        where = None
        if source_filter:
            where = {"source_dir": source_filter}

        try:
            results = self._vector_store.search(query, n_results, where)
        except Exception as e:
            return f"Search failed: {e}. Have you indexed any directories?"

        if not results:
            filter_msg = f" in '{source_filter}'" if source_filter else ""
            return f"No results found for '{query}'{filter_msg}."

        # Format results
        lines = []
        for i, result in enumerate(results, 1):
            metadata = result["metadata"]
            source = metadata.get("source_dir", "unknown")
            file_path = metadata.get("file_path", "unknown")
            start = metadata.get("start_line", "?")
            end = metadata.get("end_line", "?")
            relevance = result.get("relevance", 0) * 100

            lines.append(f"\n## Result {i} [{source}] (relevance: {relevance:.1f}%)")
            lines.append(f"**File:** {file_path}:{start}-{end}")
            lines.append("```")
            lines.append(result["content"][:500])  # Truncate long content
            if len(result["content"]) > 500:
                lines.append("... (truncated)")
            lines.append("```")

        return "\n".join(lines)

    # CLI Commands

    def add_directory_command(
        self,
        path: str,
        alias: Optional[str] = None,
    ) -> None:
        """CLI command to add a directory.

        This is registered as 'assistant add-dir'.
        """
        from rich.console import Console
        console = Console()

        try:
            dir_config = self.add_directory(path, alias)
            console.print(f"[green]Added directory:[/green] {dir_config.path}")
            console.print(f"[green]Alias:[/green] {dir_config.alias}")
            console.print("[green]Indexing complete![/green]")
        except PluginError as e:
            console.print(f"[red]Error:[/red] {e.message}")

    def list_directories_command(self) -> None:
        """CLI command to list directories.

        This is registered as 'assistant list-dirs'.
        """
        from rich.console import Console
        from rich.table import Table
        console = Console()

        dirs = self.config_manager.list_directories()
        if not dirs:
            console.print("[yellow]No directories configured.[/yellow]")
            console.print("Use 'assistant add-dir <path>' to add a directory.")
            return

        table = Table(title="Configured Directories")
        table.add_column("Alias", style="cyan")
        table.add_column("Path", style="green")
        table.add_column("Added", style="dim")
        table.add_column("Last Indexed", style="dim")

        for d in dirs:
            table.add_row(
                d.alias,
                d.path,
                d.added_at[:10] if d.added_at else "-",
                d.last_indexed[:10] if d.last_indexed else "Never",
            )

        console.print(table)

    def remove_directory_command(self, alias_or_path: str) -> None:
        """CLI command to remove a directory.

        This is registered as 'assistant remove-dir'.
        """
        from rich.console import Console
        console = Console()

        if self.remove_directory(alias_or_path):
            console.print(f"[green]Removed:[/green] {alias_or_path}")
            console.print("[yellow]Re-indexing remaining directories...[/yellow]")
        else:
            console.print(f"[red]Not found:[/red] {alias_or_path}")

    def reindex_command(self) -> None:
        """CLI command to re-index all directories.

        This is registered as 'assistant reindex'.
        """
        from rich.console import Console
        from rich.progress import Progress, SpinnerColumn, TextColumn
        console = Console()

        dirs = self.config_manager.list_directories()
        if not dirs:
            console.print("[yellow]No directories to index.[/yellow]")
            return

        console.print(f"[bold]Re-indexing {len(dirs)} directories...[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Indexing...", total=None)
            stats = self.reindex_all()
            progress.update(task, description="Complete!")

        console.print(f"\n[green]Indexed {stats['total_chunks']} chunks from {stats['total_files']} files[/green]")

        for source, source_stats in stats["by_source"].items():
            if "error" in source_stats:
                console.print(f"  [red]{source}:[/red] {source_stats['error']}")
            else:
                console.print(f"  [cyan]{source}:[/cyan] {source_stats['chunks']} chunks from {source_stats['files']} files")

    def get_config_schema(self) -> dict[str, Any]:
        """Return configuration schema."""
        return {
            "type": "object",
            "properties": {
                "unified_collection": {
                    "type": "string",
                    "description": "Name of the unified ChromaDB collection",
                    "default": "multi_codebase",
                },
            },
        }

    def configure(self, config: dict[str, Any]) -> None:
        """Apply configuration."""
        if "unified_collection" in config:
            self.config_manager.set_unified_collection(config["unified_collection"])
