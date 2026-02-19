"""RAG Guardrails plugin for anti-hallucination protection.

Ensures agent responses are grounded in the indexed codebase
by verifying claims and injecting grounding prompts.
"""

import logging
from typing import Any, Callable, Optional

# Try to import langchain tools (may not be installed)
try:
    from langchain_core.tools import BaseTool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseTool = object

from ..base import BasePlugin
from .verifier import RAGVerifier, VerificationResult, create_guardrail_prompt

logger = logging.getLogger(__name__)


class RAGGuardrailsPlugin(BasePlugin):
    """Plugin for preventing hallucinations in agent responses.

    Features:
    - Extracts verifiable claims from responses
    - Verifies claims against indexed codebase
    - Adds warnings for unverified claims
    - Injects grounding instructions into system prompts

    Modes:
    - Warning mode: Adds warnings but doesn't block responses
    - Strict mode: Refuses to output ungrounded claims
    """

    name = "rag_guardrails"
    description = "Prevents hallucination by grounding responses in indexed code"
    version = "1.0.0"
    dependencies = []

    def __init__(self):
        super().__init__()
        self.verifier = RAGVerifier()
        self.strict_mode = False
        self._show_verification = True

    def setup(self) -> None:
        """Initialize the plugin."""
        logger.info(
            f"RAG Guardrails enabled "
            f"(strict_mode={self.strict_mode})"
        )

    def teardown(self) -> None:
        """Cleanup the plugin."""
        pass

    def get_tools(self) -> list:
        """No additional tools - this plugin works via hooks."""
        return []

    def get_commands(self) -> list[Callable]:
        """Return CLI commands for guardrail configuration."""
        return [
            self.guardrails_command,
        ]

    def guardrails_command(
        self,
        strict: Optional[bool] = None,
        show_verification: Optional[bool] = None,
        status: bool = False,
    ) -> None:
        """Configure RAG guardrails.

        Args:
            strict: Enable/disable strict mode
            show_verification: Show verification results in output
            status: Show current configuration
        """
        from rich.console import Console
        console = Console()

        if strict is not None:
            self.strict_mode = strict
            console.print(
                f"[green]Strict mode:[/green] "
                f"{'enabled' if strict else 'disabled'}"
            )

        if show_verification is not None:
            self._show_verification = show_verification
            console.print(
                f"[green]Show verification:[/green] "
                f"{'enabled' if show_verification else 'disabled'}"
            )

        if status or (strict is None and show_verification is None):
            console.print("\n[bold]RAG Guardrails Configuration[/bold]")
            console.print(f"  Strict mode: {'[green]ON[/green]' if self.strict_mode else '[yellow]OFF[/yellow]'}")
            console.print(f"  Show verification: {'[green]ON[/green]' if self._show_verification else '[yellow]OFF[/yellow]'}")
            console.print("\n[dim]Strict mode blocks responses with unverified claims.[/dim]")
            console.print("[dim]Show verification displays grounding analysis in output.[/dim]")

    def get_system_prompt_addition(self) -> str:
        """Return grounding instructions for agent system prompts."""
        return create_guardrail_prompt()

    def on_agent_response(self, agent_name: str, response: dict) -> dict:
        """Post-process agent response with verification.

        Args:
            agent_name: Name of the agent that produced the response
            response: The agent's response dict

        Returns:
            Modified response with verification results
        """
        content = response.get("content", "")
        context = response.get("context", [])

        # Skip if no content
        if not content:
            return response

        # Verify the response
        result = self.verifier.verify_response(content, context)

        # Add verification metadata
        response["verification"] = {
            "grounded": result.is_grounded,
            "confidence": result.confidence,
            "verified_count": len(result.verified_claims),
            "unverified_count": len(result.unverified_claims),
        }

        # Handle unverified claims
        if not result.is_grounded:
            if self.strict_mode:
                # In strict mode, generate a grounded alternative
                response["content"] = self._generate_grounded_response(
                    content, result
                )
                response["verification"]["modified"] = True
            else:
                # In warning mode, add warnings
                if self._show_verification and result.warnings:
                    warning_text = self._format_warnings(result)
                    response["content"] = content + "\n\n" + warning_text

        # Add success indicator if showing verification
        elif self._show_verification and result.verified_claims:
            verification_text = self._format_verification_success(result)
            response["content"] = content + "\n\n" + verification_text

        return response

    def _format_warnings(self, result: VerificationResult) -> str:
        """Format verification warnings for display."""
        lines = [
            "---",
            "⚠️ **Verification Warnings**",
            "",
        ]

        for warning in result.warnings[:5]:  # Limit to 5 warnings
            lines.append(f"- {warning}")

        if len(result.warnings) > 5:
            lines.append(f"- ...and {len(result.warnings) - 5} more")

        lines.append("")
        lines.append(
            f"_Confidence: {result.confidence:.0%} "
            f"({len(result.verified_claims)}/{result.total_claims} claims verified)_"
        )

        return "\n".join(lines)

    def _format_verification_success(self, result: VerificationResult) -> str:
        """Format successful verification for display."""
        return (
            f"_✓ Response grounded "
            f"({len(result.verified_claims)} claims verified)_"
        )

    def _generate_grounded_response(
        self,
        original: str,
        result: VerificationResult,
    ) -> str:
        """Generate a response that acknowledges unverified claims.

        In strict mode, we don't output unverified claims.
        """
        lines = []

        # Keep parts of the response that are grounded
        # This is a simplified approach - a more sophisticated version
        # would rewrite the response using only verified information

        if result.verified_claims:
            lines.append("Based on the indexed codebase, I can verify:")
            lines.append("")

            for claim in result.verified_claims:
                lines.append(f"- {claim.type}: `{claim.value}`")

        if result.unverified_claims:
            lines.append("")
            lines.append(
                "⚠️ I could not verify the following in the codebase "
                "(these may be hallucinated):"
            )
            lines.append("")

            for claim in result.unverified_claims:
                lines.append(f"- {claim.type}: `{claim.value}`")

            lines.append("")
            lines.append(
                "_Note: Strict mode is enabled. Unverified claims are flagged._"
            )

        return "\n".join(lines)

    def verify_text(self, text: str, context: list[dict] = None) -> VerificationResult:
        """Manually verify a text string.

        Useful for testing or external verification.

        Args:
            text: Text to verify
            context: RAG context chunks

        Returns:
            VerificationResult
        """
        return self.verifier.verify_response(text, context or [])

    def set_vector_store(self, store) -> None:
        """Set the vector store for additional verification.

        Args:
            store: VectorStore instance
        """
        self.verifier.set_vector_store(store)

    def get_config_schema(self) -> dict[str, Any]:
        """Return configuration schema."""
        return {
            "type": "object",
            "properties": {
                "strict_mode": {
                    "type": "boolean",
                    "description": "Block responses with unverified claims",
                    "default": False,
                },
                "show_verification": {
                    "type": "boolean",
                    "description": "Show verification results in output",
                    "default": True,
                },
            },
        }

    def configure(self, config: dict[str, Any]) -> None:
        """Apply configuration."""
        if "strict_mode" in config:
            self.strict_mode = config["strict_mode"]
        if "show_verification" in config:
            self._show_verification = config["show_verification"]
