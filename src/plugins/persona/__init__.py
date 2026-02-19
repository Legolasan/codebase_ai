"""Persona plugin for role-based assistant behavior.

This plugin allows users to switch between different communication
styles and approaches by selecting a persona.

Usage:
    assistant chat --persona mentor   # Teaching-focused
    assistant chat --persona senior   # Expert, efficient
    assistant chat --persona junior   # Curious, cautious
    assistant chat --persona pair     # Collaborative
"""

from .plugin import PersonaPlugin
from .personas import PERSONAS, Persona, get_persona, list_personas

__all__ = [
    "PersonaPlugin",
    "PERSONAS",
    "Persona",
    "get_persona",
    "list_personas",
]
