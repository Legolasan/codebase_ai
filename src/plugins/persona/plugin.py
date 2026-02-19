"""Persona plugin for role-based assistant behavior.

Allows users to switch between different communication styles
by selecting a persona when starting a chat session.
"""

import logging
from typing import Any, Callable, Optional

from ..base import BasePlugin
from .personas import PERSONAS, Persona, get_persona, list_personas

logger = logging.getLogger(__name__)


class PersonaPlugin(BasePlugin):
    """Plugin for role-based personas.

    Personas modify how the assistant communicates and approaches
    problems, providing different interaction styles for different
    user needs.

    Available Personas:
    - mentor: Teaching-focused, explains concepts thoroughly
    - senior: Expert, efficient, shares best practices
    - junior: Curious, asks clarifying questions, cautious
    - pair: Collaborative pair programmer, thinks aloud

    Usage:
        assistant chat --persona mentor
        assistant chat --persona senior
        assistant chat --persona junior
        assistant chat --persona pair
    """

    name = "persona"
    description = "Role-based personas for customizing assistant behavior"
    version = "1.0.0"
    dependencies = []  # No external dependencies

    def __init__(self):
        super().__init__()
        self.active_persona: Optional[str] = None

    def setup(self) -> None:
        """Initialize the plugin."""
        logger.info("Persona plugin initialized")

    def teardown(self) -> None:
        """Cleanup the plugin."""
        self.active_persona = None

    def get_tools(self) -> list:
        """Return LangChain tools (none for this plugin)."""
        return []

    def get_commands(self) -> list[Callable]:
        """Return CLI commands (none - uses --persona flag on chat)."""
        return []

    def set_persona(self, name: str) -> Persona:
        """Set the active persona.

        Args:
            name: The persona name to activate

        Returns:
            The activated Persona

        Raises:
            ValueError: If persona name is not recognized
        """
        persona = get_persona(name)  # Validates name
        self.active_persona = name
        logger.info(f"Activated persona: {persona.emoji} {persona.name}")
        return persona

    def clear_persona(self) -> None:
        """Clear the active persona (return to default behavior)."""
        self.active_persona = None

    def get_active_persona(self) -> Optional[Persona]:
        """Get the currently active persona, if any."""
        if self.active_persona:
            return PERSONAS.get(self.active_persona)
        return None

    def get_system_prompt_addition(self) -> Optional[str]:
        """Return persona prompt if one is active.

        This is called by the plugin registry and injected into
        agent system prompts.

        Returns:
            Persona-specific prompt addition, or None if no persona active
        """
        if self.active_persona:
            persona = PERSONAS.get(self.active_persona)
            if persona:
                return f"[{persona.emoji} {persona.name} Mode]\n{persona.system_prompt_addition}"
        return None

    def get_persona_header(self) -> Optional[str]:
        """Get a formatted header for display in the chat UI.

        Returns:
            Formatted persona header string, or None if no persona active
        """
        if self.active_persona:
            persona = PERSONAS.get(self.active_persona)
            if persona:
                return f"{persona.emoji} {persona.name}"
        return None

    @staticmethod
    def list_available() -> list[str]:
        """List all available persona names."""
        return list_personas()

    @staticmethod
    def get_persona_info(name: str) -> Persona:
        """Get information about a specific persona."""
        return get_persona(name)
