"""Security Scanner Plugin.

Scans codebases for security threats including:
- Hardcoded secrets and credentials
- Malware patterns and backdoors
- Common vulnerability patterns
"""

from .plugin import SecurityScannerPlugin
from .report import SecurityReport, Finding, Severity

__all__ = [
    "SecurityScannerPlugin",
    "SecurityReport",
    "Finding",
    "Severity",
]
