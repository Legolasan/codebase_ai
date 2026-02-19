"""Plugin system for the coding assistant.

This module provides a plugin architecture that allows extending the assistant
with additional capabilities without modifying core code.

Usage:
    from plugins import PluginRegistry

    # List available plugins
    registry = PluginRegistry()
    plugins = registry.discover()

    # Enable a plugin
    registry.enable("multi_dir")

    # Get all tools from enabled plugins
    tools = registry.get_all_tools()
"""

import importlib
import json
import logging
from pathlib import Path
from typing import Any, Callable, Optional, TYPE_CHECKING

# Conditional import for type checking only
if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

from .base import BasePlugin, PluginDependencyError, PluginError, PluginInfo


logger = logging.getLogger(__name__)

# Default config directory
DEFAULT_CONFIG_DIR = Path.home() / ".assistant"


class PluginRegistry:
    """Manages plugin discovery, loading, and lifecycle.

    The registry handles:
    - Discovering plugins in the plugins/ directory
    - Loading/enabling plugins
    - Persisting enabled plugins to config
    - Aggregating tools and commands from enabled plugins

    Config is stored in ~/.assistant/plugins.json
    """

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or DEFAULT_CONFIG_DIR
        self.config_file = self.config_dir / "plugins.json"

        self._plugins: dict[str, BasePlugin] = {}
        self._enabled: set[str] = set()

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load persisted state
        self._load_config()

    def _load_config(self) -> None:
        """Load enabled plugins from config file."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    data = json.load(f)
                    self._enabled = set(data.get("enabled", []))
                    logger.debug(f"Loaded plugin config: {self._enabled}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load plugin config: {e}")
                self._enabled = set()

    def _save_config(self) -> None:
        """Save enabled plugins to config file."""
        try:
            # Load existing config to preserve plugin-specific settings
            existing = {}
            if self.config_file.exists():
                with open(self.config_file) as f:
                    existing = json.load(f)

            existing["enabled"] = list(self._enabled)

            with open(self.config_file, "w") as f:
                json.dump(existing, f, indent=2)
            logger.debug(f"Saved plugin config: {self._enabled}")
        except IOError as e:
            logger.error(f"Failed to save plugin config: {e}")

    def get_plugin_config(self, plugin_name: str) -> dict[str, Any]:
        """Get configuration for a specific plugin."""
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    data = json.load(f)
                    return data.get(plugin_name, {})
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def set_plugin_config(self, plugin_name: str, config: dict[str, Any]) -> None:
        """Set configuration for a specific plugin."""
        existing = {}
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    existing = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        existing[plugin_name] = config

        with open(self.config_file, "w") as f:
            json.dump(existing, f, indent=2)

    def discover(self) -> list[str]:
        """Auto-discover plugins in the plugins/ directory.

        Looks for subdirectories containing a plugin.py with a class
        that inherits from BasePlugin.

        Returns:
            List of discovered plugin names
        """
        plugins_dir = Path(__file__).parent
        discovered = []

        for item in plugins_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                plugin_file = item / "plugin.py"
                if plugin_file.exists():
                    try:
                        plugin = self._load_plugin(item.name)
                        if plugin:
                            self._plugins[plugin.name] = plugin
                            discovered.append(plugin.name)
                            logger.debug(f"Discovered plugin: {plugin.name}")
                    except Exception as e:
                        logger.warning(f"Failed to load plugin {item.name}: {e}")

        return discovered

    def _load_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        """Load a plugin by name.

        Args:
            plugin_name: Name of the plugin directory

        Returns:
            Plugin instance or None if loading fails
        """
        try:
            module = importlib.import_module(f".{plugin_name}.plugin", package="plugins")

            # Find the plugin class (first class inheriting from BasePlugin)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BasePlugin)
                    and attr is not BasePlugin
                ):
                    return attr()

            logger.warning(f"No plugin class found in {plugin_name}/plugin.py")
            return None

        except ImportError as e:
            logger.debug(f"Could not import plugin {plugin_name}: {e}")
            return None

    def get(self, plugin_name: str) -> Optional[BasePlugin]:
        """Get a plugin by name.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin instance or None if not found
        """
        if plugin_name not in self._plugins:
            # Try to load it
            plugin = self._load_plugin(plugin_name)
            if plugin:
                self._plugins[plugin_name] = plugin

        return self._plugins.get(plugin_name)

    def list_all(self) -> list[PluginInfo]:
        """List all discovered plugins with their status.

        Returns:
            List of PluginInfo objects
        """
        self.discover()
        return [
            PluginInfo(
                name=plugin.name,
                description=plugin.description,
                version=plugin.version,
                dependencies=plugin.dependencies,
                enabled=plugin.name in self._enabled,
            )
            for plugin in self._plugins.values()
        ]

    def enable(self, plugin_name: str) -> None:
        """Enable a plugin.

        Checks dependencies, calls setup(), and persists the enabled state.

        Args:
            plugin_name: Name of the plugin to enable

        Raises:
            PluginError: If plugin not found
            PluginDependencyError: If dependencies are missing
        """
        plugin = self.get(plugin_name)
        if not plugin:
            raise PluginError(plugin_name, "Plugin not found")

        if plugin_name in self._enabled:
            logger.debug(f"Plugin {plugin_name} already enabled")
            return

        # Check dependencies
        if not plugin.is_available():
            missing = plugin.get_missing_dependencies()
            raise PluginDependencyError(plugin_name, missing)

        # Load plugin-specific config
        config = self.get_plugin_config(plugin_name)
        if config:
            plugin.configure(config)

        # Setup plugin
        try:
            plugin.setup()
            plugin._enabled = True
            self._enabled.add(plugin_name)
            self._save_config()
            logger.info(f"Enabled plugin: {plugin_name}")
        except Exception as e:
            raise PluginError(plugin_name, f"Setup failed: {e}")

    def disable(self, plugin_name: str) -> None:
        """Disable a plugin.

        Calls teardown() and persists the disabled state.

        Args:
            plugin_name: Name of the plugin to disable
        """
        plugin = self.get(plugin_name)
        if not plugin:
            return

        if plugin_name not in self._enabled:
            logger.debug(f"Plugin {plugin_name} already disabled")
            return

        try:
            plugin.teardown()
        except Exception as e:
            logger.warning(f"Plugin {plugin_name} teardown error: {e}")

        plugin._enabled = False
        self._enabled.discard(plugin_name)
        self._save_config()
        logger.info(f"Disabled plugin: {plugin_name}")

    def is_enabled(self, plugin_name: str) -> bool:
        """Check if a plugin is enabled."""
        return plugin_name in self._enabled

    def get_enabled(self) -> list[BasePlugin]:
        """Get all enabled plugins."""
        return [
            plugin
            for name, plugin in self._plugins.items()
            if name in self._enabled and plugin._enabled
        ]

    def initialize_enabled(self) -> None:
        """Initialize all plugins that should be enabled.

        Called at startup to restore previously enabled plugins.
        """
        self.discover()
        for plugin_name in list(self._enabled):
            try:
                plugin = self.get(plugin_name)
                if plugin and not plugin._enabled:
                    if plugin.is_available():
                        config = self.get_plugin_config(plugin_name)
                        if config:
                            plugin.configure(config)
                        plugin.setup()
                        plugin._enabled = True
                        logger.info(f"Initialized plugin: {plugin_name}")
                    else:
                        logger.warning(
                            f"Plugin {plugin_name} unavailable, missing deps: "
                            f"{plugin.get_missing_dependencies()}"
                        )
            except Exception as e:
                logger.error(f"Failed to initialize plugin {plugin_name}: {e}")
                self._enabled.discard(plugin_name)

    def get_all_tools(self) -> list:
        """Aggregate tools from all enabled plugins.

        Returns:
            Combined list of tools from all enabled plugins
        """
        tools = []
        for plugin in self.get_enabled():
            try:
                plugin_tools = plugin.get_tools()
                tools.extend(plugin_tools)
            except Exception as e:
                logger.error(f"Failed to get tools from {plugin.name}: {e}")
        return tools

    def get_all_commands(self) -> list[Callable]:
        """Aggregate CLI commands from all enabled plugins.

        Returns:
            Combined list of command functions from all enabled plugins
        """
        commands = []
        for plugin in self.get_enabled():
            try:
                plugin_commands = plugin.get_commands()
                commands.extend(plugin_commands)
            except Exception as e:
                logger.error(f"Failed to get commands from {plugin.name}: {e}")
        return commands

    def get_system_prompt_additions(self) -> str:
        """Get combined system prompt additions from all enabled plugins.

        Returns:
            Combined prompt string to append to agent system prompts
        """
        additions = []
        for plugin in self.get_enabled():
            try:
                addition = plugin.get_system_prompt_addition()
                if addition:
                    additions.append(f"[{plugin.name}]\n{addition}")
            except Exception as e:
                logger.error(f"Failed to get prompt from {plugin.name}: {e}")
        return "\n\n".join(additions) if additions else ""

    def process_agent_response(self, agent_name: str, response: dict) -> dict:
        """Run all plugin response hooks on an agent response.

        Args:
            agent_name: Name of the agent
            response: The agent's response dict

        Returns:
            Processed response dict
        """
        for plugin in self.get_enabled():
            try:
                response = plugin.on_agent_response(agent_name, response)
            except Exception as e:
                logger.error(f"Plugin {plugin.name} response hook failed: {e}")
        return response

    def process_tool_call(self, tool_name: str, args: dict) -> dict:
        """Run all plugin tool call hooks.

        Args:
            tool_name: Name of the tool being called
            args: Arguments passed to the tool

        Returns:
            Possibly modified args dict
        """
        for plugin in self.get_enabled():
            try:
                modified = plugin.on_tool_call(tool_name, args)
                if modified is not None:
                    args = modified
            except Exception as e:
                logger.error(f"Plugin {plugin.name} tool hook failed: {e}")
        return args


# Global registry instance
_registry: Optional[PluginRegistry] = None


def get_registry() -> PluginRegistry:
    """Get the global plugin registry instance."""
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def reset_registry() -> None:
    """Reset the global registry (for testing)."""
    global _registry
    _registry = None


# Re-export base classes
__all__ = [
    "BasePlugin",
    "PluginInfo",
    "PluginError",
    "PluginDependencyError",
    "PluginRegistry",
    "get_registry",
    "reset_registry",
]
