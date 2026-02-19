"""MCP client adapter for Context7.

Provides async connection to the Context7 MCP server for
library documentation and research capabilities.
"""

import asyncio
import logging
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class LibraryInfo:
    """Information about a resolved library."""

    library_id: str
    name: str
    description: str
    version: Optional[str] = None


@dataclass
class DocumentationResult:
    """Result from documentation lookup."""

    content: str
    library_id: str
    topic: Optional[str] = None
    source_url: Optional[str] = None


class Context7Client:
    """Client for interacting with Context7 MCP server.

    Context7 provides up-to-date library documentation via MCP,
    useful for competitor analysis and feature research.

    The client can operate in two modes:
    1. MCP mode: Uses langchain-mcp-adapters for full MCP protocol
    2. HTTP mode: Falls back to direct HTTP API calls
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Context7 client.

        Args:
            api_key: Context7 API key (falls back to CONTEXT7_API_KEY env var)
        """
        self.api_key = api_key or os.environ.get("CONTEXT7_API_KEY")
        self._mcp_client = None
        self._http_client = None
        self._connected = False

    @property
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return self.api_key is not None

    async def connect(self) -> bool:
        """Connect to the Context7 MCP server.

        Returns:
            True if connection successful
        """
        if not self.api_key:
            logger.warning("Context7 API key not configured")
            return False

        # Try MCP connection first
        if await self._connect_mcp():
            self._connected = True
            return True

        # Fall back to HTTP mode
        logger.info("Falling back to Context7 HTTP mode")
        self._connected = True
        return True

    async def _connect_mcp(self) -> bool:
        """Attempt to connect via MCP protocol."""
        try:
            # Check if MCP adapters are available
            from langchain_mcp_adapters.client import MultiServerMCPClient

            self._mcp_client = MultiServerMCPClient({
                "context7": {
                    "transport": "stdio",
                    "command": "npx",
                    "args": ["-y", "@upstash/context7-mcp"],
                    "env": {"CONTEXT7_API_KEY": self.api_key},
                }
            })

            await self._mcp_client.__aenter__()
            logger.info("Connected to Context7 via MCP")
            return True

        except ImportError:
            logger.debug("langchain-mcp-adapters not available")
            return False
        except Exception as e:
            logger.debug(f"MCP connection failed: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from the Context7 server."""
        if self._mcp_client:
            try:
                await self._mcp_client.__aexit__(None, None, None)
            except Exception:
                pass
            self._mcp_client = None

        self._connected = False

    def get_tools(self) -> list:
        """Get LangChain tools from Context7 MCP.

        Returns:
            List of LangChain tools, or empty list if not connected via MCP
        """
        if self._mcp_client:
            try:
                from langchain_mcp_adapters.tools import load_mcp_tools
                return load_mcp_tools(self._mcp_client)
            except Exception as e:
                logger.error(f"Failed to load MCP tools: {e}")

        return []

    async def resolve_library(self, library_name: str) -> Optional[LibraryInfo]:
        """Resolve a library name to its Context7 ID.

        Args:
            library_name: Name of the library (e.g., "react", "fastapi")

        Returns:
            LibraryInfo if found, None otherwise
        """
        if self._mcp_client:
            return await self._resolve_library_mcp(library_name)
        else:
            return await self._resolve_library_http(library_name)

    async def _resolve_library_mcp(self, library_name: str) -> Optional[LibraryInfo]:
        """Resolve library via MCP."""
        try:
            # Call the resolve-library-id MCP tool
            result = await self._call_mcp_tool(
                "resolve-library-id",
                {"libraryName": library_name}
            )

            if result and "libraryId" in result:
                return LibraryInfo(
                    library_id=result["libraryId"],
                    name=result.get("name", library_name),
                    description=result.get("description", ""),
                    version=result.get("version"),
                )
        except Exception as e:
            logger.error(f"Failed to resolve library via MCP: {e}")

        return None

    async def _resolve_library_http(self, library_name: str) -> Optional[LibraryInfo]:
        """Resolve library via HTTP API fallback."""
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.context7.com/v1/libraries/resolve",
                    params={"name": library_name},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10,
                )

                if response.status_code == 200:
                    data = response.json()
                    return LibraryInfo(
                        library_id=data["id"],
                        name=data.get("name", library_name),
                        description=data.get("description", ""),
                        version=data.get("version"),
                    )
        except Exception as e:
            logger.debug(f"HTTP library resolution failed: {e}")

        return None

    async def get_documentation(
        self,
        library_id: str,
        topic: Optional[str] = None,
        max_tokens: int = 5000,
    ) -> Optional[DocumentationResult]:
        """Get documentation for a library.

        Args:
            library_id: Context7 library ID
            topic: Specific topic to look up (optional)
            max_tokens: Maximum tokens to return

        Returns:
            DocumentationResult if found
        """
        if self._mcp_client:
            return await self._get_docs_mcp(library_id, topic, max_tokens)
        else:
            return await self._get_docs_http(library_id, topic, max_tokens)

    async def _get_docs_mcp(
        self,
        library_id: str,
        topic: Optional[str],
        max_tokens: int,
    ) -> Optional[DocumentationResult]:
        """Get documentation via MCP."""
        try:
            params = {
                "context7CompatibleLibraryID": library_id,
                "tokens": max_tokens,
            }
            if topic:
                params["topic"] = topic

            result = await self._call_mcp_tool("get-library-docs", params)

            if result and "content" in result:
                return DocumentationResult(
                    content=result["content"],
                    library_id=library_id,
                    topic=topic,
                    source_url=result.get("source_url"),
                )
        except Exception as e:
            logger.error(f"Failed to get docs via MCP: {e}")

        return None

    async def _get_docs_http(
        self,
        library_id: str,
        topic: Optional[str],
        max_tokens: int,
    ) -> Optional[DocumentationResult]:
        """Get documentation via HTTP API fallback."""
        try:
            import httpx

            params = {
                "libraryId": library_id,
                "maxTokens": max_tokens,
            }
            if topic:
                params["topic"] = topic

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.context7.com/v1/docs",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30,
                )

                if response.status_code == 200:
                    data = response.json()
                    return DocumentationResult(
                        content=data["content"],
                        library_id=library_id,
                        topic=topic,
                        source_url=data.get("source_url"),
                    )
        except Exception as e:
            logger.debug(f"HTTP docs fetch failed: {e}")

        return None

    async def _call_mcp_tool(self, tool_name: str, params: dict) -> Optional[dict]:
        """Call an MCP tool.

        Args:
            tool_name: Name of the MCP tool
            params: Tool parameters

        Returns:
            Tool result or None
        """
        if not self._mcp_client:
            return None

        try:
            # Find the tool
            tools = self.get_tools()
            for tool in tools:
                if tool.name == tool_name:
                    result = await tool.ainvoke(params)
                    return result
        except Exception as e:
            logger.error(f"MCP tool call failed: {e}")

        return None

    async def research_topic(
        self,
        topic: str,
        libraries: Optional[list[str]] = None,
    ) -> list[DocumentationResult]:
        """Research a topic across multiple libraries.

        Args:
            topic: Research topic
            libraries: Specific libraries to search (optional)

        Returns:
            List of documentation results
        """
        results = []

        # If libraries specified, search those
        if libraries:
            for lib_name in libraries:
                lib_info = await self.resolve_library(lib_name)
                if lib_info:
                    docs = await self.get_documentation(
                        lib_info.library_id,
                        topic=topic,
                    )
                    if docs:
                        results.append(docs)

        return results


def check_context7_available() -> dict:
    """Check if Context7 is available and configured.

    Returns:
        Dict with availability status
    """
    status = {
        "configured": False,
        "api_key_set": bool(os.environ.get("CONTEXT7_API_KEY")),
        "mcp_available": False,
        "npx_available": False,
    }

    # Check for MCP adapters
    try:
        import langchain_mcp_adapters
        status["mcp_available"] = True
    except ImportError:
        pass

    # Check for npx (required for MCP server)
    try:
        result = subprocess.run(
            ["npx", "--version"],
            capture_output=True,
            timeout=5,
        )
        status["npx_available"] = result.returncode == 0
    except Exception:
        pass

    status["configured"] = status["api_key_set"]

    return status
