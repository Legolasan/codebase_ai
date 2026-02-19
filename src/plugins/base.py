"""Base plugin class for the assistant plugin system."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TYPE_CHECKING

# Conditional import for type checking only
if TYPE_CHECKING:
    from langchain_core.tools import BaseTool


@dataclass
class PluginInfo:
    """Metadata about a plugin."""

    name: str
    description: str
    version: str
    dependencies: list[str] = field(default_factory=list)
    author: str = ""
    enabled: bool = False


class BasePlugin(ABC):
    """Base class for all plugins.

    Plugins extend the assistant with additional capabilities such as:
    - New tools for agents to use
    - CLI commands for users
    - Hooks into the agent workflow
    - Custom configuration options

    Lifecycle:
    1. Plugin is discovered via PluginRegistry.discover()
    2. Plugin is enabled via PluginRegistry.enable()
    3. setup() is called to initialize the plugin
    4. Plugin tools/commands are available
    5. teardown() is called when disabled
    """

    # Plugin metadata - must be set by subclasses
    name: str = "base"
    description: str = "Base plugin"
    version: str = "0.0.0"
    dependencies: list[str] = []

    def __init__(self):
        self._enabled = False
        self._tools: list[BaseTool] = []
        self._commands: list[Callable] = []

    @property
    def info(self) -> PluginInfo:
        """Get plugin metadata."""
        return PluginInfo(
            name=self.name,
            description=self.description,
            version=self.version,
            dependencies=self.dependencies,
            enabled=self._enabled,
        )

    @property
    def is_enabled(self) -> bool:
        """Check if plugin is currently enabled."""
        return self._enabled

    def is_available(self) -> bool:
        """Check if all dependencies are satisfied.

        Override to add custom availability checks (e.g., API keys).
        """
        return self._check_dependencies()

    def _check_dependencies(self) -> bool:
        """Check if required pip packages are installed."""
        import importlib.util

        for dep in self.dependencies:
            # Handle package names that differ from import names
            import_name = dep.split("[")[0]  # Remove extras like "package[extra]"
            import_name = import_name.replace("-", "_")  # Common convention

            if importlib.util.find_spec(import_name) is None:
                return False
        return True

    def get_missing_dependencies(self) -> list[str]:
        """Return list of missing dependencies."""
        import importlib.util

        missing = []
        for dep in self.dependencies:
            import_name = dep.split("[")[0].replace("-", "_")
            if importlib.util.find_spec(import_name) is None:
                missing.append(dep)
        return missing

    @abstractmethod
    def setup(self) -> None:
        """Initialize the plugin.

        Called once when the plugin is enabled. Use this to:
        - Load configuration
        - Initialize connections
        - Set up resources

        Raises:
            PluginError: If setup fails
        """
        pass

    @abstractmethod
    def teardown(self) -> None:
        """Cleanup the plugin.

        Called when the plugin is disabled. Use this to:
        - Close connections
        - Save state
        - Release resources
        """
        pass

    @abstractmethod
    def get_tools(self) -> list:
        """Return LangChain tools provided by this plugin.

        These tools will be made available to agents when the plugin is enabled.

        Returns:
            List of LangChain BaseTool instances
        """
        pass

    @abstractmethod
    def get_commands(self) -> list[Callable]:
        """Return CLI commands to register.

        These commands will be added to the main CLI when the plugin is enabled.
        Commands should be Typer-compatible functions.

        Returns:
            List of command functions
        """
        pass

    def get_config_schema(self) -> Optional[dict[str, Any]]:
        """Return JSON schema for plugin configuration.

        Override to define plugin-specific configuration options.

        Returns:
            JSON schema dict or None if no config needed
        """
        return None

    def configure(self, config: dict[str, Any]) -> None:
        """Apply configuration to the plugin.

        Args:
            config: Configuration dict matching the schema from get_config_schema()
        """
        pass

    def get_system_prompt_addition(self) -> Optional[str]:
        """Return text to add to agent system prompts.

        Use this to inject plugin-specific instructions into agents.

        Returns:
            String to append to system prompts, or None
        """
        return None

    def on_agent_response(self, agent_name: str, response: dict) -> dict:
        """Hook called after each agent response.

        Override to post-process or validate agent responses.

        Args:
            agent_name: Name of the agent that produced the response
            response: The agent's response dict

        Returns:
            Modified response dict
        """
        return response

    def on_tool_call(self, tool_name: str, args: dict) -> Optional[dict]:
        """Hook called before each tool call.

        Override to intercept or modify tool calls.

        Args:
            tool_name: Name of the tool being called
            args: Arguments passed to the tool

        Returns:
            Modified args dict, or None to proceed with original args
        """
        return None

    def __repr__(self) -> str:
        status = "enabled" if self._enabled else "disabled"
        return f"<{self.__class__.__name__}({self.name} v{self.version}, {status})>"


class PluginError(Exception):
    """Exception raised by plugins."""

    def __init__(self, plugin_name: str, message: str):
        self.plugin_name = plugin_name
        self.message = message
        super().__init__(f"[{plugin_name}] {message}")


class PluginDependencyError(PluginError):
    """Exception raised when plugin dependencies are missing."""

    def __init__(self, plugin_name: str, missing_deps: list[str]):
        self.missing_deps = missing_deps
        deps_str = ", ".join(missing_deps)
        super().__init__(
            plugin_name,
            f"Missing dependencies: {deps_str}. Install with: pip install {' '.join(missing_deps)}"
        )
