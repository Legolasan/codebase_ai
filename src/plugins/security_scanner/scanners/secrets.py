"""Secret detection scanner.

Detects hardcoded credentials, API keys, and other sensitive data.
"""

import logging
from typing import Iterator

from ..patterns import SECRET_PATTERNS, Pattern
from ..report import Finding

logger = logging.getLogger(__name__)


class SecretScanner:
    """Scanner for detecting hardcoded secrets and credentials."""

    def __init__(self, patterns: list[Pattern] | None = None):
        """Initialize the secret scanner.

        Args:
            patterns: Custom patterns to use. Defaults to SECRET_PATTERNS.
        """
        self.patterns = patterns or SECRET_PATTERNS

    def scan_content(
        self,
        content: str,
        file_path: str,
    ) -> Iterator[Finding]:
        """Scan content for secrets.

        Args:
            content: File content to scan
            file_path: Path to the file (for reporting)

        Yields:
            Finding objects for each detected secret
        """
        lines = content.split("\n")

        for line_num, line in enumerate(lines, start=1):
            # Skip empty lines and comments
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("//"):
                continue

            for pattern in self.patterns:
                match = pattern.pattern.search(line)
                if not match:
                    continue

                # Check exclusion pattern
                if pattern.exclude_if and pattern.exclude_if.search(line):
                    logger.debug(
                        f"Excluded match for {pattern.name} at {file_path}:{line_num}"
                    )
                    continue

                # Check required context if specified
                if pattern.requires_context:
                    if not pattern.requires_context.search(content):
                        continue

                # Extract matched text (try to get the captured group if any)
                matched_text = match.group(1) if match.lastindex else match.group(0)

                # Mask the secret in the matched text for reporting
                if len(matched_text) > 8:
                    masked = matched_text[:4] + "*" * (len(matched_text) - 8) + matched_text[-4:]
                else:
                    masked = "*" * len(matched_text)

                yield Finding(
                    severity=pattern.severity,
                    category=pattern.category,
                    pattern_name=pattern.name,
                    file_path=file_path,
                    line_number=line_num,
                    line_content=line,
                    description=f"{pattern.description}. Found: {masked}",
                    recommendation=pattern.recommendation,
                    matched_text=matched_text,
                )

    def scan_file(self, file_path: str) -> list[Finding]:
        """Scan a file for secrets.

        Args:
            file_path: Path to the file to scan

        Returns:
            List of findings
        """
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return list(self.scan_content(content, file_path))
        except Exception as e:
            logger.warning(f"Failed to scan {file_path}: {e}")
            return []
