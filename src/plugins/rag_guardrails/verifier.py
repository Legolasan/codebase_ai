"""Response verification for RAG-grounded responses.

Extracts claims from responses and verifies them against the
indexed codebase to prevent hallucinations.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Claim:
    """A verifiable claim extracted from a response."""

    type: str  # "file", "function", "code_snippet", "line_reference"
    value: str
    context: str  # Surrounding text for context
    verified: bool = False
    source: Optional[str] = None  # Where it was verified (if found)


@dataclass
class VerificationResult:
    """Result of verifying a response."""

    is_grounded: bool
    verified_claims: list[Claim] = field(default_factory=list)
    unverified_claims: list[Claim] = field(default_factory=list)
    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)

    @property
    def total_claims(self) -> int:
        return len(self.verified_claims) + len(self.unverified_claims)


class RAGVerifier:
    """Verifies agent responses against indexed codebase.

    Extracts claims (file references, function names, code snippets)
    from responses and verifies they exist in the RAG context.
    """

    # Patterns for extracting claims
    FILE_PATH_PATTERN = re.compile(
        r'(?:file[:\s]+|in\s+)?'  # Optional prefix
        r'[`"]?'  # Optional backtick or quote
        r'([\w./\\-]+\.(?:py|js|ts|tsx|jsx|java|go|rs|cpp|c|h|rb|php|swift|kt|scala|md|json|yaml|yml|toml|sh))'
        r'[`"]?',  # Optional closing
        re.IGNORECASE
    )

    LINE_REF_PATTERN = re.compile(
        r'([\w./\\-]+\.(?:py|js|ts|tsx|jsx|java|go|rs|cpp|c|h))'  # File path
        r'[:\s]+'  # Separator
        r'(?:lines?\s*)?'  # Optional "line" prefix
        r'(\d+)(?:\s*[-–to]+\s*(\d+))?',  # Line number(s)
        re.IGNORECASE
    )

    FUNCTION_PATTERN = re.compile(
        r'(?:function|method|def|class|func)\s+'
        r'[`"]?'
        r'([\w_]+)'
        r'[`"]?',
        re.IGNORECASE
    )

    CODE_BLOCK_PATTERN = re.compile(
        r'```(?:\w+)?\n(.*?)```',
        re.DOTALL
    )

    def __init__(self, vector_store=None):
        """Initialize the verifier.

        Args:
            vector_store: Optional VectorStore instance for verification
        """
        self._vector_store = vector_store
        self._context_cache: dict[str, list[dict]] = {}

    def set_vector_store(self, store) -> None:
        """Set the vector store for verification."""
        self._vector_store = store

    def verify_response(
        self,
        response: str,
        context: list[dict] = None,
    ) -> VerificationResult:
        """Verify that response claims are grounded in context.

        Args:
            response: The agent's response text
            context: RAG context chunks (list of dicts with 'content', 'metadata')

        Returns:
            VerificationResult with grounding status
        """
        context = context or []

        # Extract all claims from the response
        claims = self._extract_claims(response)

        if not claims:
            # No verifiable claims - assume grounded
            return VerificationResult(
                is_grounded=True,
                confidence=1.0,
            )

        # Build searchable context
        context_text = self._build_context_text(context)
        context_files = self._extract_context_files(context)

        # Verify each claim
        verified = []
        unverified = []

        for claim in claims:
            if self._verify_claim(claim, context_text, context_files, context):
                claim.verified = True
                verified.append(claim)
            else:
                unverified.append(claim)

        # Calculate confidence
        confidence = len(verified) / len(claims) if claims else 1.0

        # Generate warnings for unverified claims
        warnings = []
        for claim in unverified:
            warnings.append(
                f"Could not verify {claim.type}: '{claim.value}'"
            )

        return VerificationResult(
            is_grounded=len(unverified) == 0,
            verified_claims=verified,
            unverified_claims=unverified,
            confidence=confidence,
            warnings=warnings,
        )

    def _extract_claims(self, response: str) -> list[Claim]:
        """Extract verifiable claims from response text."""
        claims = []

        # Extract file path claims
        for match in self.FILE_PATH_PATTERN.finditer(response):
            file_path = match.group(1)
            # Skip common false positives
            if not self._is_likely_file_path(file_path):
                continue

            claims.append(Claim(
                type="file",
                value=file_path,
                context=self._get_context_window(response, match.start(), match.end()),
            ))

        # Extract line reference claims
        for match in self.LINE_REF_PATTERN.finditer(response):
            file_path = match.group(1)
            start_line = match.group(2)
            end_line = match.group(3) or start_line

            claims.append(Claim(
                type="line_reference",
                value=f"{file_path}:{start_line}-{end_line}",
                context=self._get_context_window(response, match.start(), match.end()),
            ))

        # Extract function/class name claims
        for match in self.FUNCTION_PATTERN.finditer(response):
            name = match.group(1)
            # Skip common names that are probably not specific functions
            if name.lower() in {"main", "init", "test", "run", "get", "set"}:
                continue

            claims.append(Claim(
                type="function",
                value=name,
                context=self._get_context_window(response, match.start(), match.end()),
            ))

        # Extract code snippet claims (for longer snippets)
        for match in self.CODE_BLOCK_PATTERN.finditer(response):
            code = match.group(1).strip()
            # Only verify substantial code blocks
            if len(code) > 50 and "\n" in code:
                claims.append(Claim(
                    type="code_snippet",
                    value=code[:200],  # Truncate for comparison
                    context=self._get_context_window(response, match.start(), match.end()),
                ))

        return claims

    def _is_likely_file_path(self, path: str) -> bool:
        """Check if a string is likely a real file path."""
        # Skip very short paths
        if len(path) < 4:
            return False

        # Skip paths that look like URLs
        if path.startswith(("http://", "https://", "ftp://")):
            return False

        # Skip common false positives
        false_positives = {
            "example.py", "test.py", "main.py", "app.py",
            "index.js", "index.ts", "app.js", "app.ts",
            "package.json", "config.json", "settings.json",
        }
        if path.lower() in false_positives:
            return False

        return True

    def _get_context_window(self, text: str, start: int, end: int, window: int = 50) -> str:
        """Get surrounding context for a match."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end]

    def _build_context_text(self, context: list[dict]) -> str:
        """Build searchable text from context chunks."""
        parts = []
        for chunk in context:
            content = chunk.get("content", "")
            metadata = chunk.get("metadata", {})
            file_path = metadata.get("file_path", "")

            parts.append(f"FILE: {file_path}\n{content}")

        return "\n\n".join(parts)

    def _extract_context_files(self, context: list[dict]) -> set[str]:
        """Extract file paths from context."""
        files = set()
        for chunk in context:
            metadata = chunk.get("metadata", {})
            file_path = metadata.get("file_path", "")
            if file_path:
                files.add(file_path)
                # Also add basename
                files.add(Path(file_path).name)

        return files

    def _verify_claim(
        self,
        claim: Claim,
        context_text: str,
        context_files: set[str],
        context: list[dict],
    ) -> bool:
        """Verify a single claim against context."""

        if claim.type == "file":
            # Check if file exists in context
            file_path = claim.value
            if file_path in context_files:
                claim.source = "RAG context"
                return True

            # Check basename
            basename = Path(file_path).name
            if basename in context_files:
                claim.source = "RAG context (basename match)"
                return True

            # Try vector store search if available
            if self._vector_store:
                try:
                    results = self._vector_store.search_by_file(file_path)
                    if results:
                        claim.source = "Vector store"
                        return True
                except Exception:
                    pass

            return False

        elif claim.type == "line_reference":
            # Parse the reference
            parts = claim.value.split(":")
            if len(parts) < 2:
                return False

            file_path = parts[0]
            line_range = parts[1]

            # First verify the file exists
            if file_path not in context_files:
                basename = Path(file_path).name
                if basename not in context_files:
                    return False

            # Check if line numbers are reasonable
            for chunk in context:
                metadata = chunk.get("metadata", {})
                if file_path in metadata.get("file_path", "") or \
                   Path(file_path).name == Path(metadata.get("file_path", "")).name:
                    start_line = metadata.get("start_line", 0)
                    end_line = metadata.get("end_line", 0)

                    # Parse claimed line range
                    try:
                        if "-" in line_range:
                            claimed_start, claimed_end = map(int, line_range.split("-"))
                        else:
                            claimed_start = claimed_end = int(line_range)

                        # Check if claimed range overlaps with chunk
                        if start_line <= claimed_end and claimed_start <= end_line:
                            claim.source = "RAG context"
                            return True
                    except ValueError:
                        pass

            return False

        elif claim.type == "function":
            # Check if function name appears in context
            func_name = claim.value
            patterns = [
                f"def {func_name}",
                f"function {func_name}",
                f"class {func_name}",
                f"func {func_name}",
                f"const {func_name}",
                f"let {func_name}",
                f"var {func_name}",
            ]

            for pattern in patterns:
                if pattern in context_text:
                    claim.source = "RAG context"
                    return True

            # Also check just the name
            if func_name in context_text:
                claim.source = "RAG context (name match)"
                return True

            return False

        elif claim.type == "code_snippet":
            # Check if significant part of snippet appears in context
            snippet = claim.value

            # Extract distinctive lines from snippet
            lines = [line.strip() for line in snippet.split("\n") if line.strip()]

            # Require majority of non-trivial lines to match
            matches = 0
            total = 0

            for line in lines:
                # Skip trivial lines
                if len(line) < 10 or line in {"{", "}", ")", "(", ":", "pass", "return"}:
                    continue

                total += 1
                if line in context_text:
                    matches += 1

            if total > 0 and matches / total >= 0.5:
                claim.source = "RAG context (partial match)"
                return True

            return False

        return False


def create_guardrail_prompt() -> str:
    """Create the system prompt addition for RAG grounding.

    Returns:
        String to append to agent system prompts
    """
    return """
IMPORTANT: You MUST ground ALL responses in the indexed codebase.

Rules:
1. ONLY reference files that exist in the codebase context provided
2. ONLY cite code that appears in the RAG results
3. If asked about something not in the codebase, say "I don't have information about that in the indexed codebase"
4. ALWAYS include file:line references for code claims
5. NEVER invent or hallucinate file names, function names, or code

If the codebase doesn't contain relevant information, acknowledge this limitation.
You may use your general knowledge to explain concepts, but specific code claims must be verifiable.
"""
