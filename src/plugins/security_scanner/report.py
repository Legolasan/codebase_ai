"""Security report formatting and data classes."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class Severity(Enum):
    """Severity levels for security findings."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"

    @property
    def emoji(self) -> str:
        """Get emoji for severity level."""
        return {
            Severity.CRITICAL: "\U0001f534",  # Red circle
            Severity.HIGH: "\U0001f7e0",      # Orange circle
            Severity.MEDIUM: "\U0001f7e1",    # Yellow circle
            Severity.LOW: "\U0001f535",       # Blue circle
            Severity.INFO: "\u2139\ufe0f",    # Info
        }[self]

    @property
    def color(self) -> str:
        """Get rich color for severity level."""
        return {
            Severity.CRITICAL: "red bold",
            Severity.HIGH: "red",
            Severity.MEDIUM: "yellow",
            Severity.LOW: "blue",
            Severity.INFO: "dim",
        }[self]


@dataclass
class Finding:
    """A single security finding."""
    severity: Severity
    category: str  # secret, malware, vulnerability
    pattern_name: str  # e.g., "AWS Access Key"
    file_path: str
    line_number: int
    line_content: str
    description: str
    recommendation: str
    matched_text: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert finding to dictionary."""
        return {
            "severity": self.severity.value,
            "category": self.category,
            "pattern_name": self.pattern_name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "line_content": self.line_content,
            "description": self.description,
            "recommendation": self.recommendation,
        }


@dataclass
class SecurityReport:
    """Security scan report with all findings."""
    scan_time: datetime = field(default_factory=datetime.now)
    files_scanned: int = 0
    findings: list[Finding] = field(default_factory=list)
    scan_duration_ms: float = 0.0
    root_path: str = ""

    @property
    def summary(self) -> dict[str, int]:
        """Count findings by severity."""
        counts = {s.value: 0 for s in Severity}
        for finding in self.findings:
            counts[finding.severity.value] += 1
        return counts

    def has_critical(self) -> bool:
        """Check if any critical issues found."""
        return any(f.severity == Severity.CRITICAL for f in self.findings)

    def has_high_or_critical(self) -> bool:
        """Check if any high or critical issues found."""
        return any(
            f.severity in (Severity.CRITICAL, Severity.HIGH)
            for f in self.findings
        )

    def get_by_severity(self, severity: Severity) -> list[Finding]:
        """Get findings of a specific severity."""
        return [f for f in self.findings if f.severity == severity]

    def get_by_category(self, category: str) -> list[Finding]:
        """Get findings of a specific category."""
        return [f for f in self.findings if f.category == category]

    def to_summary(self) -> str:
        """Generate a short summary string."""
        total = len(self.findings)
        if total == 0:
            return "No security issues found."

        parts = []
        for severity in Severity:
            count = self.summary[severity.value]
            if count > 0:
                parts.append(f"{count} {severity.value}")

        return f"Found {total} issues: " + ", ".join(parts)

    def to_markdown(self) -> str:
        """Format report as markdown."""
        lines = [
            "# Security Scan Report",
            "",
            f"**Scan Time:** {self.scan_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Files Scanned:** {self.files_scanned}",
            f"**Duration:** {self.scan_duration_ms:.1f}ms",
            f"**Path:** {self.root_path}",
            "",
            "## Summary",
            "",
        ]

        # Summary table
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        for severity in Severity:
            count = self.summary[severity.value]
            if count > 0:
                lines.append(f"| {severity.emoji} {severity.value} | {count} |")

        lines.append("")
        lines.append(f"**Total Issues:** {len(self.findings)}")
        lines.append("")

        if not self.findings:
            lines.append("No security issues found.")
            return "\n".join(lines)

        # Group findings by severity
        lines.append("## Findings")
        lines.append("")

        for severity in Severity:
            findings = self.get_by_severity(severity)
            if not findings:
                continue

            lines.append(f"### {severity.emoji} {severity.value} ({len(findings)})")
            lines.append("")

            for i, finding in enumerate(findings, 1):
                lines.append(f"#### {i}. {finding.pattern_name}")
                lines.append("")
                lines.append(f"**File:** `{finding.file_path}:{finding.line_number}`")
                lines.append(f"**Category:** {finding.category}")
                lines.append("")
                lines.append("**Code:**")
                lines.append("```")
                # Truncate long lines
                line_content = finding.line_content
                if len(line_content) > 200:
                    line_content = line_content[:200] + "..."
                lines.append(line_content)
                lines.append("```")
                lines.append("")
                lines.append(f"**Description:** {finding.description}")
                lines.append("")
                lines.append(f"**Recommendation:** {finding.recommendation}")
                lines.append("")
                lines.append("---")
                lines.append("")

        return "\n".join(lines)

    def to_console(self) -> str:
        """Format report for console output (rich-compatible)."""
        lines = [
            "",
            "[bold]Security Scan Results[/bold]",
            "=" * 40,
            "",
            f"Scanned: {self.files_scanned} files",
            f"Time: {self.scan_duration_ms:.1f}ms",
            "",
        ]

        if not self.findings:
            lines.append("[green]No security issues found.[/green]")
            return "\n".join(lines)

        # Group by severity
        for severity in Severity:
            findings = self.get_by_severity(severity)
            if not findings:
                continue

            lines.append(f"[{severity.color}]{severity.emoji} {severity.value} ({len(findings)})[/{severity.color}]")

            for finding in findings:
                # File path and line
                lines.append(f"  [dim]{finding.file_path}:{finding.line_number}[/dim] - {finding.pattern_name}")

                # Show truncated code line
                code = finding.line_content.strip()
                if len(code) > 60:
                    code = code[:60] + "..."
                lines.append(f"    [dim]{code}[/dim]")

                # Recommendation
                lines.append(f"    [italic]{finding.recommendation}[/italic]")
                lines.append("")

        lines.append("")
        lines.append(f"Run '[cyan]assistant security report[/cyan]' for full details.")

        return "\n".join(lines)
