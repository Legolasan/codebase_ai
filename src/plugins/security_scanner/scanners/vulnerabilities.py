"""Vulnerability pattern detection scanner.

Detects common security vulnerabilities like SQL injection, XSS, command injection, etc.
"""

import logging
from typing import Iterator

from ..patterns import VULNERABILITY_PATTERNS, Pattern
from ..report import Finding

logger = logging.getLogger(__name__)


class VulnerabilityScanner:
    """Scanner for detecting common vulnerability patterns."""

    def __init__(self, patterns: list[Pattern] | None = None):
        """Initialize the vulnerability scanner.

        Args:
            patterns: Custom patterns to use. Defaults to VULNERABILITY_PATTERNS.
        """
        self.patterns = patterns or VULNERABILITY_PATTERNS

    def scan_content(
        self,
        content: str,
        file_path: str,
    ) -> Iterator[Finding]:
        """Scan content for vulnerability patterns.

        Args:
            content: File content to scan
            file_path: Path to the file (for reporting)

        Yields:
            Finding objects for each detected vulnerability
        """
        lines = content.split("\n")

        # Skip test files by default for some patterns
        is_test_file = self._is_test_file(file_path)

        for line_num, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped:
                continue

            # Skip comment lines
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("*"):
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

                # Skip debug mode warnings in test files
                if is_test_file and "debug" in pattern.name.lower():
                    continue

                yield Finding(
                    severity=pattern.severity,
                    category=pattern.category,
                    pattern_name=pattern.name,
                    file_path=file_path,
                    line_number=line_num,
                    line_content=line,
                    description=pattern.description,
                    recommendation=pattern.recommendation,
                    matched_text=match.group(0),
                )

    def scan_file(self, file_path: str) -> list[Finding]:
        """Scan a file for vulnerabilities.

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

    def _is_test_file(self, file_path: str) -> bool:
        """Check if a file is a test file.

        Args:
            file_path: Path to check

        Returns:
            True if this appears to be a test file
        """
        test_indicators = [
            "/test/",
            "/tests/",
            "/spec/",
            "/specs/",
            "_test.",
            ".test.",
            "_spec.",
            ".spec.",
            "test_",
            "spec_",
            "/fixtures/",
            "/mocks/",
            "__tests__",
        ]
        file_lower = file_path.lower()
        return any(indicator in file_lower for indicator in test_indicators)

    def get_vulnerability_summary(self, findings: list[Finding]) -> dict:
        """Generate a summary of vulnerability findings by category.

        Args:
            findings: List of findings to summarize

        Returns:
            Dictionary with vulnerability categories and counts
        """
        summary = {
            "injection": {"count": 0, "types": []},
            "xss": {"count": 0, "types": []},
            "crypto": {"count": 0, "types": []},
            "config": {"count": 0, "types": []},
            "other": {"count": 0, "types": []},
        }

        injection_keywords = ["sql", "command", "injection", "shell"]
        xss_keywords = ["xss", "html", "template", "unsafe"]
        crypto_keywords = ["md5", "sha1", "ecb", "crypto", "ssl"]
        config_keywords = ["debug", "cors", "ip", "config"]

        for finding in findings:
            name_lower = finding.pattern_name.lower()

            if any(kw in name_lower for kw in injection_keywords):
                summary["injection"]["count"] += 1
                if finding.pattern_name not in summary["injection"]["types"]:
                    summary["injection"]["types"].append(finding.pattern_name)
            elif any(kw in name_lower for kw in xss_keywords):
                summary["xss"]["count"] += 1
                if finding.pattern_name not in summary["xss"]["types"]:
                    summary["xss"]["types"].append(finding.pattern_name)
            elif any(kw in name_lower for kw in crypto_keywords):
                summary["crypto"]["count"] += 1
                if finding.pattern_name not in summary["crypto"]["types"]:
                    summary["crypto"]["types"].append(finding.pattern_name)
            elif any(kw in name_lower for kw in config_keywords):
                summary["config"]["count"] += 1
                if finding.pattern_name not in summary["config"]["types"]:
                    summary["config"]["types"].append(finding.pattern_name)
            else:
                summary["other"]["count"] += 1
                if finding.pattern_name not in summary["other"]["types"]:
                    summary["other"]["types"].append(finding.pattern_name)

        return summary
