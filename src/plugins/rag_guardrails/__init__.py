"""RAG Guardrails plugin for anti-hallucination protection.

This plugin ensures agent responses are grounded in the indexed
codebase, preventing hallucinated file names, function names, or code.
"""

from .plugin import RAGGuardrailsPlugin

__all__ = ["RAGGuardrailsPlugin"]
