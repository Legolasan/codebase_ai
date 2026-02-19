"""Security Scanner Plugin.

Main plugin class that orchestrates security scanning across a codebase.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, TYPE_CHECKING

# Try to import langchain tools (may not be installed)
try:
    from langchain_core.tools import tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    def tool(func):
        return func

from ..base import BasePlugin
from .report import SecurityReport, Finding, Severity
from .scanners import SecretScanner, MalwareScanner, VulnerabilityScanner

logger = logging.getLogger(__name__)


# File extensions to scan
SCANNABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",  # Python & JavaScript
    ".java", ".kt", ".scala",              # JVM languages
    ".go", ".rs",                          # Go & Rust
    ".rb", ".php",                         # Ruby & PHP
    ".cs", ".vb",                          # .NET
    ".sh", ".bash", ".zsh",                # Shell scripts
    ".yml", ".yaml", ".json",              # Config files
    ".env", ".ini", ".cfg", ".conf",       # Environment/config
    ".sql",                                # SQL files
    ".html", ".htm", ".xml",               # Markup
    ".c", ".cpp", ".h", ".hpp",            # C/C++
}

# Files to always skip
SKIP_FILES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Cargo.lock",
    "poetry.lock",
    "Pipfile.lock",
    "composer.lock",
}

# Directories to skip
SKIP_DIRS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".env",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "target",
    ".idea",
    ".vscode",
    "vendor",
    ".tox",
    ".pytest_cache",
    ".mypy_cache",
    "coverage",
    ".coverage",
    "htmlcov",
}


class SecurityScannerPlugin(BasePlugin):
    """Plugin for scanning codebases for security issues.

    Features:
    - Secret detection (API keys, passwords, tokens)
    - Malware pattern detection (backdoors, reverse shells)
    - Vulnerability scanning (SQL injection, XSS, etc.)
    - Automatic scanning on index
    - On-demand CLI scanning
    """

    name = "security_scanner"
    description = "Scans codebase for malicious code, secrets, and vulnerabilities"
    version = "1.0.0"
    dependencies = []  # Uses only built-in packages

    def __init__(self):
        super().__init__()
        self.secret_scanner = SecretScanner()
        self.malware_scanner = MalwareScanner()
        self.vuln_scanner = VulnerabilityScanner()

        # Configuration
        self.auto_scan_on_index = True
        self.scan_secrets = True
        self.scan_malware = True
        self.scan_vulnerabilities = True

        # Last scan result
        self._last_report: Optional[SecurityReport] = None

    def setup(self) -> None:
        """Initialize the plugin."""
        logger.info("Security scanner plugin initialized")

    def teardown(self) -> None:
        """Cleanup the plugin."""
        self._last_report = None

    def get_tools(self) -> list:
        """Return LangChain tools for security scanning."""
        if not LANGCHAIN_AVAILABLE:
            return []
        return [
            self._create_scan_tool(),
            self._create_report_tool(),
        ]

    def get_commands(self) -> list[Callable]:
        """Return CLI commands for security scanning."""
        return []  # Commands are registered directly in main.py

    def _create_scan_tool(self):
        """Create the security scan tool for agents."""
        plugin = self

        @tool
        def security_scan(
            path: Optional[str] = None,
            secrets_only: bool = False,
            malware_only: bool = False,
            vulns_only: bool = False,
        ) -> str:
            """Scan code for security issues, secrets, and vulnerabilities.

            Args:
                path: Directory to scan. Defaults to current codebase.
                secrets_only: Only scan for secrets/credentials
                malware_only: Only scan for malware patterns
                vulns_only: Only scan for vulnerability patterns

            Returns:
                Security report with findings
            """
            report = plugin.scan_codebase(
                path or ".",
                scan_secrets=not (malware_only or vulns_only) or secrets_only,
                scan_malware=not (secrets_only or vulns_only) or malware_only,
                scan_vulnerabilities=not (secrets_only or malware_only) or vulns_only,
            )
            return report.to_console()

        return security_scan

    def _create_report_tool(self):
        """Create the security report tool for agents."""
        plugin = self

        @tool
        def get_security_report() -> str:
            """Get the last security scan report in detail.

            Returns:
                Detailed markdown security report
            """
            if plugin._last_report is None:
                return "No security scan has been run yet. Use security_scan() first."
            return plugin._last_report.to_markdown()

        return get_security_report

    def scan_file(
        self,
        file_path: str,
        content: Optional[str] = None,
        scan_secrets: bool = True,
        scan_malware: bool = True,
        scan_vulnerabilities: bool = True,
    ) -> list[Finding]:
        """Scan a single file for security issues.

        Args:
            file_path: Path to the file
            content: Optional file content (reads file if not provided)
            scan_secrets: Whether to scan for secrets
            scan_malware: Whether to scan for malware patterns
            scan_vulnerabilities: Whether to scan for vulnerabilities

        Returns:
            List of findings
        """
        findings = []

        # Read content if not provided
        if content is None:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")
                return findings

        # Run scanners
        if scan_secrets:
            findings.extend(self.secret_scanner.scan_content(content, file_path))

        if scan_malware:
            findings.extend(self.malware_scanner.scan_content(content, file_path))

        if scan_vulnerabilities:
            findings.extend(self.vuln_scanner.scan_content(content, file_path))

        return findings

    def scan_codebase(
        self,
        root_dir: str,
        scan_secrets: bool = True,
        scan_malware: bool = True,
        scan_vulnerabilities: bool = True,
    ) -> SecurityReport:
        """Scan entire codebase and return report.

        Args:
            root_dir: Root directory to scan
            scan_secrets: Whether to scan for secrets
            scan_malware: Whether to scan for malware patterns
            scan_vulnerabilities: Whether to scan for vulnerabilities

        Returns:
            SecurityReport with all findings
        """
        start_time = time.time()
        root_path = Path(root_dir).resolve()

        report = SecurityReport(
            scan_time=datetime.now(),
            root_path=str(root_path),
        )

        if not root_path.exists():
            logger.error(f"Path does not exist: {root_path}")
            return report

        # Collect files to scan
        files_to_scan = self._collect_files(root_path)
        report.files_scanned = len(files_to_scan)

        logger.info(f"Scanning {len(files_to_scan)} files in {root_path}")

        # Scan each file
        for file_path in files_to_scan:
            try:
                findings = self.scan_file(
                    str(file_path),
                    scan_secrets=scan_secrets,
                    scan_malware=scan_malware,
                    scan_vulnerabilities=scan_vulnerabilities,
                )
                report.findings.extend(findings)
            except Exception as e:
                logger.warning(f"Error scanning {file_path}: {e}")

        # Calculate duration
        report.scan_duration_ms = (time.time() - start_time) * 1000

        # Store last report
        self._last_report = report

        logger.info(
            f"Scan complete: {len(report.findings)} findings in "
            f"{report.files_scanned} files ({report.scan_duration_ms:.1f}ms)"
        )

        return report

    def _collect_files(self, root_path: Path) -> list[Path]:
        """Collect all scannable files in a directory.

        Args:
            root_path: Root directory to search

        Returns:
            List of file paths to scan
        """
        files = []

        for item in root_path.rglob("*"):
            # Skip directories in skip list
            if any(skip_dir in item.parts for skip_dir in SKIP_DIRS):
                continue

            # Skip non-files
            if not item.is_file():
                continue

            # Skip files in skip list
            if item.name in SKIP_FILES:
                continue

            # Check extension
            if item.suffix.lower() not in SCANNABLE_EXTENSIONS:
                # Also scan files without extension that might be scripts
                if item.suffix and item.suffix.lower() != "":
                    continue

            # Skip large files (> 1MB)
            try:
                if item.stat().st_size > 1_000_000:
                    logger.debug(f"Skipping large file: {item}")
                    continue
            except OSError:
                continue

            files.append(item)

        return files

    def on_index_complete(self, indexed_files: list) -> SecurityReport:
        """Hook called after indexing - triggers auto-scan.

        Args:
            indexed_files: List of files that were indexed

        Returns:
            SecurityReport from the scan
        """
        if not self.auto_scan_on_index:
            return SecurityReport()

        logger.info("Running security scan after index...")

        # Scan the indexed files
        report = SecurityReport(scan_time=datetime.now())
        start_time = time.time()

        for file_info in indexed_files:
            file_path = file_info.get("path", file_info) if isinstance(file_info, dict) else str(file_info)
            try:
                findings = self.scan_file(str(file_path))
                report.findings.extend(findings)
                report.files_scanned += 1
            except Exception as e:
                logger.warning(f"Error scanning {file_path}: {e}")

        report.scan_duration_ms = (time.time() - start_time) * 1000
        self._last_report = report

        return report

    def get_config_schema(self) -> dict[str, Any]:
        """Return configuration schema."""
        return {
            "type": "object",
            "properties": {
                "auto_scan_on_index": {
                    "type": "boolean",
                    "description": "Automatically scan when codebase is indexed",
                    "default": True,
                },
                "scan_secrets": {
                    "type": "boolean",
                    "description": "Scan for hardcoded secrets",
                    "default": True,
                },
                "scan_malware": {
                    "type": "boolean",
                    "description": "Scan for malware patterns",
                    "default": True,
                },
                "scan_vulnerabilities": {
                    "type": "boolean",
                    "description": "Scan for vulnerability patterns",
                    "default": True,
                },
            },
        }

    def configure(self, config: dict[str, Any]) -> None:
        """Apply configuration."""
        if "auto_scan_on_index" in config:
            self.auto_scan_on_index = config["auto_scan_on_index"]
        if "scan_secrets" in config:
            self.scan_secrets = config["scan_secrets"]
        if "scan_malware" in config:
            self.scan_malware = config["scan_malware"]
        if "scan_vulnerabilities" in config:
            self.scan_vulnerabilities = config["scan_vulnerabilities"]

    def get_system_prompt_addition(self) -> Optional[str]:
        """Return text to add to agent system prompts."""
        return """
You have access to a security scanner that can detect:
- Hardcoded secrets (API keys, passwords, tokens)
- Malware patterns (backdoors, reverse shells, crypto miners)
- Common vulnerabilities (SQL injection, XSS, command injection)

Use the security_scan tool to check code for security issues before deployment.
Always recommend fixing CRITICAL and HIGH severity issues immediately.
"""

    def get_last_report(self) -> Optional[SecurityReport]:
        """Get the last security scan report."""
        return self._last_report

    # CLI command implementations (called from main.py)

    def scan_command(
        self,
        path: Optional[str] = None,
        secrets_only: bool = False,
        malware_only: bool = False,
        vulns_only: bool = False,
    ) -> None:
        """CLI command to run a security scan."""
        from rich.console import Console
        from rich.progress import Progress, SpinnerColumn, TextColumn

        console = Console()

        scan_path = path or "."
        console.print(f"\n[bold]Scanning:[/bold] {Path(scan_path).resolve()}\n")

        # Determine what to scan
        scan_secrets = not (malware_only or vulns_only) or secrets_only
        scan_malware = not (secrets_only or vulns_only) or malware_only
        scan_vulns = not (secrets_only or malware_only) or vulns_only

        scan_types = []
        if scan_secrets:
            scan_types.append("secrets")
        if scan_malware:
            scan_types.append("malware")
        if scan_vulns:
            scan_types.append("vulnerabilities")

        console.print(f"[dim]Scanning for: {', '.join(scan_types)}[/dim]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Scanning...", total=None)
            report = self.scan_codebase(
                scan_path,
                scan_secrets=scan_secrets,
                scan_malware=scan_malware,
                scan_vulnerabilities=scan_vulns,
            )
            progress.update(task, description="Complete!")

        # Print results
        self._print_report(console, report)

    def report_command(self, output: Optional[str] = None) -> None:
        """CLI command to generate a detailed report."""
        from rich.console import Console
        from rich.markdown import Markdown

        console = Console()

        if self._last_report is None:
            console.print("[yellow]No scan has been run yet.[/yellow]")
            console.print("Run 'assistant security scan' first.")
            return

        if output:
            # Save to file
            report_md = self._last_report.to_markdown()
            output_path = Path(output)
            output_path.write_text(report_md)
            console.print(f"[green]Report saved to:[/green] {output_path}")
        else:
            # Print to console
            console.print(Markdown(self._last_report.to_markdown()))

    def status_command(self) -> None:
        """CLI command to show security scanner status."""
        from rich.console import Console
        from rich.table import Table

        console = Console()

        table = Table(title="Security Scanner Status")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Auto-scan on index", str(self.auto_scan_on_index))
        table.add_row("Scan secrets", str(self.scan_secrets))
        table.add_row("Scan malware", str(self.scan_malware))
        table.add_row("Scan vulnerabilities", str(self.scan_vulnerabilities))

        console.print(table)

        if self._last_report:
            console.print(f"\n[bold]Last Scan:[/bold]")
            console.print(f"  Time: {self._last_report.scan_time}")
            console.print(f"  Files: {self._last_report.files_scanned}")
            console.print(f"  Findings: {len(self._last_report.findings)}")
            console.print(f"  {self._last_report.to_summary()}")
        else:
            console.print("\n[dim]No scans have been run yet.[/dim]")

    def auto_scan_command(self, enable: bool) -> None:
        """CLI command to enable/disable auto-scan."""
        from rich.console import Console
        from ..base import PluginError

        console = Console()

        self.auto_scan_on_index = enable

        # Save to plugin config
        try:
            from .. import get_registry
            registry = get_registry()
            config = registry.get_plugin_config(self.name)
            config["auto_scan_on_index"] = enable
            registry.set_plugin_config(self.name, config)
        except Exception as e:
            logger.warning(f"Failed to save config: {e}")

        status = "[green]enabled[/green]" if enable else "[yellow]disabled[/yellow]"
        console.print(f"Auto-scan on index: {status}")

    def _print_report(self, console, report: SecurityReport) -> None:
        """Print a security report to the console."""
        console.print(f"\n[bold]Security Scan Results[/bold]")
        console.print("=" * 40)
        console.print(f"\nScanned: {report.files_scanned} files")
        console.print(f"Time: {report.scan_duration_ms:.1f}ms\n")

        if not report.findings:
            console.print("[green]No security issues found.[/green]")
            return

        # Group by severity
        for severity in Severity:
            findings = report.get_by_severity(severity)
            if not findings:
                continue

            console.print(f"[{severity.color}]{severity.emoji} {severity.value} ({len(findings)})[/{severity.color}]")

            for finding in findings[:5]:  # Limit to 5 per severity
                # File path and line
                console.print(f"  [dim]{finding.file_path}:{finding.line_number}[/dim] - {finding.pattern_name}")

                # Show truncated code line
                code = finding.line_content.strip()
                if len(code) > 60:
                    code = code[:60] + "..."
                console.print(f"    [dim]{code}[/dim]")

                # Recommendation
                console.print(f"    [italic]{finding.recommendation}[/italic]")
                console.print()

            if len(findings) > 5:
                console.print(f"  [dim]... and {len(findings) - 5} more[/dim]\n")

        console.print(f"\nRun '[cyan]assistant security report[/cyan]' for full details.")

        # Alert on critical issues
        if report.has_critical():
            console.print("\n[red bold]CRITICAL security issues found! Please review immediately.[/red bold]")
