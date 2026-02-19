"""Security detection patterns.

Centralized regex patterns for detecting security issues.
"""

import re
from dataclasses import dataclass
from typing import Optional

from .report import Severity


@dataclass
class Pattern:
    """A security detection pattern."""
    name: str
    pattern: re.Pattern
    severity: Severity
    category: str  # secret, malware, vulnerability
    description: str
    recommendation: str
    # Optional: only match if this pattern is also present
    requires_context: Optional[re.Pattern] = None
    # Optional: don't match if this pattern is present (false positive filter)
    exclude_if: Optional[re.Pattern] = None


# =============================================================================
# Secret Detection Patterns
# =============================================================================

SECRET_PATTERNS = [
    # AWS Keys
    Pattern(
        name="AWS Access Key ID",
        pattern=re.compile(r'AKIA[0-9A-Z]{16}', re.IGNORECASE),
        severity=Severity.CRITICAL,
        category="secret",
        description="AWS Access Key ID found in source code",
        recommendation="Use environment variables or AWS Secrets Manager",
    ),
    Pattern(
        name="AWS Secret Access Key",
        pattern=re.compile(
            r'(?:aws_secret_access_key|aws_secret|secret_access_key)\s*[=:]\s*["\']?([A-Za-z0-9/+=]{40})["\']?',
            re.IGNORECASE
        ),
        severity=Severity.CRITICAL,
        category="secret",
        description="AWS Secret Access Key found in source code",
        recommendation="Use environment variables or AWS Secrets Manager",
    ),

    # GitHub Tokens
    Pattern(
        name="GitHub Personal Access Token",
        pattern=re.compile(r'ghp_[A-Za-z0-9]{36}'),
        severity=Severity.CRITICAL,
        category="secret",
        description="GitHub Personal Access Token found",
        recommendation="Use GitHub secrets or environment variables",
    ),
    Pattern(
        name="GitHub OAuth Token",
        pattern=re.compile(r'gho_[A-Za-z0-9]{36}'),
        severity=Severity.HIGH,
        category="secret",
        description="GitHub OAuth Token found",
        recommendation="Use secure token storage",
    ),
    Pattern(
        name="GitHub App Token",
        pattern=re.compile(r'(?:ghu|ghs)_[A-Za-z0-9]{36}'),
        severity=Severity.HIGH,
        category="secret",
        description="GitHub App Token found",
        recommendation="Use secure token storage",
    ),

    # Generic API Keys
    Pattern(
        name="Generic API Key",
        pattern=re.compile(
            r'(?:api[_-]?key|apikey|api[_-]?secret)\s*[=:]\s*["\']([A-Za-z0-9_\-]{20,})["\']',
            re.IGNORECASE
        ),
        severity=Severity.HIGH,
        category="secret",
        description="Possible API key found in source code",
        recommendation="Use environment variables or a secrets manager",
        exclude_if=re.compile(r'example|test|fake|dummy|placeholder', re.IGNORECASE),
    ),

    # Private Keys
    Pattern(
        name="RSA Private Key",
        pattern=re.compile(r'-----BEGIN RSA PRIVATE KEY-----'),
        severity=Severity.CRITICAL,
        category="secret",
        description="RSA private key found in source code",
        recommendation="Store private keys in secure key management systems, not in code",
    ),
    Pattern(
        name="SSH Private Key",
        pattern=re.compile(r'-----BEGIN OPENSSH PRIVATE KEY-----'),
        severity=Severity.CRITICAL,
        category="secret",
        description="SSH private key found in source code",
        recommendation="Store private keys securely, never commit to version control",
    ),
    Pattern(
        name="PGP Private Key",
        pattern=re.compile(r'-----BEGIN PGP PRIVATE KEY BLOCK-----'),
        severity=Severity.CRITICAL,
        category="secret",
        description="PGP private key found in source code",
        recommendation="Store private keys securely outside the codebase",
    ),

    # Passwords
    Pattern(
        name="Hardcoded Password",
        pattern=re.compile(
            r'(?:password|passwd|pwd|secret)\s*[=:]\s*["\']([^"\']{8,})["\']',
            re.IGNORECASE
        ),
        severity=Severity.HIGH,
        category="secret",
        description="Hardcoded password found",
        recommendation="Use environment variables or a secrets manager for credentials",
        exclude_if=re.compile(r'example|test|fake|dummy|placeholder|\$\{|process\.env|os\.environ', re.IGNORECASE),
    ),

    # JWT Secrets
    Pattern(
        name="JWT Secret",
        pattern=re.compile(
            r'(?:jwt[_-]?secret|jwt[_-]?key|signing[_-]?secret)\s*[=:]\s*["\']([^"\']{16,})["\']',
            re.IGNORECASE
        ),
        severity=Severity.CRITICAL,
        category="secret",
        description="JWT signing secret found in source code",
        recommendation="Use environment variables for JWT secrets",
        exclude_if=re.compile(r'example|test|fake|dummy', re.IGNORECASE),
    ),

    # Database Connection Strings
    Pattern(
        name="Database Connection String with Credentials",
        pattern=re.compile(
            r'(?:postgres|mysql|mongodb|redis)(?:ql)?://[^:]+:[^@]+@[^/\s]+',
            re.IGNORECASE
        ),
        severity=Severity.CRITICAL,
        category="secret",
        description="Database connection string with embedded credentials",
        recommendation="Use environment variables for database credentials",
    ),

    # Slack Tokens
    Pattern(
        name="Slack Token",
        pattern=re.compile(r'xox[baprs]-[0-9A-Za-z\-]{10,}'),
        severity=Severity.HIGH,
        category="secret",
        description="Slack token found in source code",
        recommendation="Use environment variables for Slack tokens",
    ),

    # Stripe Keys
    Pattern(
        name="Stripe Secret Key",
        pattern=re.compile(r'sk_live_[A-Za-z0-9]{24,}'),
        severity=Severity.CRITICAL,
        category="secret",
        description="Stripe live secret key found",
        recommendation="Use environment variables for Stripe keys",
    ),
    Pattern(
        name="Stripe Publishable Key (Test)",
        pattern=re.compile(r'pk_test_[A-Za-z0-9]{24,}'),
        severity=Severity.LOW,
        category="secret",
        description="Stripe test publishable key found (generally safe but review)",
        recommendation="Consider using environment variables even for test keys",
    ),

    # Google API Key
    Pattern(
        name="Google API Key",
        pattern=re.compile(r'AIza[0-9A-Za-z\-_]{35}'),
        severity=Severity.HIGH,
        category="secret",
        description="Google API key found in source code",
        recommendation="Use environment variables and restrict API key permissions",
    ),

    # Twilio
    Pattern(
        name="Twilio Account SID",
        pattern=re.compile(r'AC[a-z0-9]{32}', re.IGNORECASE),
        severity=Severity.HIGH,
        category="secret",
        description="Twilio Account SID found",
        recommendation="Use environment variables for Twilio credentials",
    ),

    # SendGrid
    Pattern(
        name="SendGrid API Key",
        pattern=re.compile(r'SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}'),
        severity=Severity.HIGH,
        category="secret",
        description="SendGrid API key found",
        recommendation="Use environment variables for SendGrid keys",
    ),

    # Heroku
    Pattern(
        name="Heroku API Key",
        pattern=re.compile(
            r'(?:heroku[_-]?api[_-]?key|HEROKU_API_KEY)\s*[=:]\s*["\']?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})["\']?',
            re.IGNORECASE
        ),
        severity=Severity.HIGH,
        category="secret",
        description="Heroku API key found",
        recommendation="Use environment variables or Heroku config vars",
    ),
]


# =============================================================================
# Malware Detection Patterns
# =============================================================================

MALWARE_PATTERNS = [
    # Reverse shells
    Pattern(
        name="Potential Reverse Shell",
        pattern=re.compile(
            r'(?:socket\.connect|subprocess).*(?:bash|sh|cmd|powershell)',
            re.IGNORECASE | re.DOTALL
        ),
        severity=Severity.CRITICAL,
        category="malware",
        description="Code pattern resembling a reverse shell",
        recommendation="Review this code carefully - may be a backdoor",
    ),
    Pattern(
        name="Network Shell Command",
        pattern=re.compile(
            r'(?:nc|netcat|ncat)\s+.*\s+(?:-e|-c)\s+(?:/bin/(?:ba)?sh|cmd)',
            re.IGNORECASE
        ),
        severity=Severity.CRITICAL,
        category="malware",
        description="Netcat reverse shell pattern detected",
        recommendation="Remove or audit this code immediately",
    ),

    # Crypto miners
    Pattern(
        name="Crypto Mining Pool URL",
        pattern=re.compile(
            r'(?:stratum\+tcp|pool\.).*(?:\.com|\.org|\.net|:\d+)',
            re.IGNORECASE
        ),
        severity=Severity.HIGH,
        category="malware",
        description="Cryptocurrency mining pool URL detected",
        recommendation="Investigate for unauthorized crypto mining code",
    ),
    Pattern(
        name="Crypto Wallet Address",
        pattern=re.compile(
            r'(?:^|[^A-Za-z0-9])(?:bc1|[13])[A-HJ-NP-Za-km-z1-9]{25,39}(?:[^A-Za-z0-9]|$)'
        ),
        severity=Severity.MEDIUM,
        category="malware",
        description="Bitcoin wallet address found",
        recommendation="Review context - may be legitimate or crypto miner",
    ),

    # Data exfiltration patterns
    Pattern(
        name="Potential Data Exfiltration",
        pattern=re.compile(
            r'(?:requests\.post|http\.post|fetch\s*\().*(?:password|secret|key|token|credential)',
            re.IGNORECASE | re.DOTALL
        ),
        severity=Severity.HIGH,
        category="malware",
        description="Sensitive data being sent via HTTP",
        recommendation="Verify this is legitimate data transmission",
    ),

    # Obfuscated code
    Pattern(
        name="Base64 Encoded Execution",
        pattern=re.compile(
            r'(?:base64\.b64decode|atob|Buffer\.from\([^)]+,\s*["\']base64["\']).*(?:exec|eval|compile)',
            re.IGNORECASE | re.DOTALL
        ),
        severity=Severity.HIGH,
        category="malware",
        description="Base64 decoded content being executed",
        recommendation="Decode and review the content being executed",
    ),
    Pattern(
        name="Eval with String Concatenation",
        pattern=re.compile(
            r'eval\s*\(\s*(?:["\'][^"\']+["\']|\w+)\s*\+',
            re.IGNORECASE
        ),
        severity=Severity.MEDIUM,
        category="malware",
        description="Eval with string concatenation (possible obfuscation)",
        recommendation="Review and refactor to avoid eval",
    ),

    # Keylogger patterns
    Pattern(
        name="Keyboard Hook",
        pattern=re.compile(
            r'(?:SetWindowsHookEx|keyboard|pynput|keylogger).*(?:WH_KEYBOARD|on_press|log)',
            re.IGNORECASE | re.DOTALL
        ),
        severity=Severity.CRITICAL,
        category="malware",
        description="Keyboard monitoring/logging pattern detected",
        recommendation="Review for keylogger behavior",
    ),

    # Hidden imports
    Pattern(
        name="Dynamic Import Obfuscation",
        pattern=re.compile(
            r'__import__\s*\(\s*(?:["\'][A-Za-z0-9_]+["\']|(?:chr\([^)]+\)\s*\+?\s*)+)',
        ),
        severity=Severity.MEDIUM,
        category="malware",
        description="Obfuscated dynamic import pattern",
        recommendation="Review what module is being imported",
    ),

    # Backdoor admin access
    Pattern(
        name="Hardcoded Backdoor Credentials",
        pattern=re.compile(
            r'(?:admin|root|backdoor|master)[_-]?(?:user|pass|pwd|password)\s*[=:]\s*["\'][^"\']+["\']',
            re.IGNORECASE
        ),
        severity=Severity.CRITICAL,
        category="malware",
        description="Possible backdoor credentials",
        recommendation="Remove hardcoded backdoor access immediately",
    ),
]


# =============================================================================
# Vulnerability Detection Patterns
# =============================================================================

VULNERABILITY_PATTERNS = [
    # SQL Injection
    Pattern(
        name="SQL Injection Risk",
        pattern=re.compile(
            r'(?:execute|cursor\.execute|query)\s*\(\s*(?:f["\']|["\'].*%|.*\.format\(|.*\+)',
            re.IGNORECASE
        ),
        severity=Severity.CRITICAL,
        category="vulnerability",
        description="SQL query with string interpolation (SQL injection risk)",
        recommendation="Use parameterized queries instead of string formatting",
    ),
    Pattern(
        name="Raw SQL String Concatenation",
        pattern=re.compile(
            r'(?:SELECT|INSERT|UPDATE|DELETE|DROP)\s+.*\+\s*(?:\w+|["\'])',
            re.IGNORECASE
        ),
        severity=Severity.HIGH,
        category="vulnerability",
        description="SQL with string concatenation",
        recommendation="Use parameterized queries or an ORM",
    ),

    # Command Injection
    Pattern(
        name="Command Injection Risk",
        pattern=re.compile(
            r'(?:os\.system|subprocess\.(?:call|run|Popen)|exec)\s*\(\s*(?:f["\']|.*\.format|.*\+|.*%)',
            re.IGNORECASE
        ),
        severity=Severity.CRITICAL,
        category="vulnerability",
        description="Shell command with user-controlled input",
        recommendation="Use subprocess with shell=False and validate/sanitize inputs",
    ),
    Pattern(
        name="Unsafe Shell=True",
        pattern=re.compile(
            r'subprocess\.\w+\s*\([^)]*shell\s*=\s*True',
            re.IGNORECASE
        ),
        severity=Severity.HIGH,
        category="vulnerability",
        description="subprocess with shell=True is dangerous",
        recommendation="Use shell=False with a command list instead",
    ),

    # Path Traversal
    Pattern(
        name="Path Traversal Risk",
        pattern=re.compile(
            r'(?:open|read|write|Path)\s*\(\s*(?:request|user|input|args|params)',
            re.IGNORECASE
        ),
        severity=Severity.HIGH,
        category="vulnerability",
        description="File operation with user input (path traversal risk)",
        recommendation="Validate and sanitize file paths, use os.path.basename",
    ),

    # XSS
    Pattern(
        name="XSS Risk - Unescaped Output",
        pattern=re.compile(
            r'(?:innerHTML|outerHTML|document\.write)\s*[+=]\s*(?:request|user|input|\$)',
            re.IGNORECASE
        ),
        severity=Severity.HIGH,
        category="vulnerability",
        description="Unescaped user input in HTML (XSS risk)",
        recommendation="Sanitize user input before inserting into HTML",
    ),
    Pattern(
        name="Unsafe Template Rendering",
        pattern=re.compile(
            r'(?:\{\{\s*\w+\s*\|?\s*safe\s*\}\}|render_template_string)',
            re.IGNORECASE
        ),
        severity=Severity.MEDIUM,
        category="vulnerability",
        description="Template rendering may bypass HTML escaping",
        recommendation="Ensure user data is properly escaped",
    ),

    # Insecure Deserialization
    Pattern(
        name="Insecure Pickle Deserialization",
        pattern=re.compile(
            r'pickle\.loads?\s*\(\s*(?:request|user|input|data|body)',
            re.IGNORECASE
        ),
        severity=Severity.CRITICAL,
        category="vulnerability",
        description="Pickle deserialization of untrusted data",
        recommendation="Never unpickle untrusted data - use JSON or safe alternatives",
    ),
    Pattern(
        name="Unsafe YAML Loading",
        pattern=re.compile(
            r'yaml\.(?:load|unsafe_load)\s*\([^)]*(?:Loader\s*=\s*(?:yaml\.)?(?:Loader|UnsafeLoader|FullLoader))?',
            re.IGNORECASE
        ),
        severity=Severity.HIGH,
        category="vulnerability",
        description="Unsafe YAML loading allows arbitrary code execution",
        recommendation="Use yaml.safe_load() instead",
        exclude_if=re.compile(r'safe_load|SafeLoader'),
    ),

    # Weak Cryptography
    Pattern(
        name="MD5 for Security",
        pattern=re.compile(
            r'(?:md5|hashlib\.md5)\s*\([^)]*(?:password|secret|key|token)',
            re.IGNORECASE
        ),
        severity=Severity.HIGH,
        category="vulnerability",
        description="MD5 used for security purposes (weak hash)",
        recommendation="Use bcrypt, scrypt, or argon2 for passwords; SHA-256+ for hashing",
    ),
    Pattern(
        name="SHA1 for Security",
        pattern=re.compile(
            r'(?:sha1|hashlib\.sha1)\s*\([^)]*(?:password|secret|key|token)',
            re.IGNORECASE
        ),
        severity=Severity.MEDIUM,
        category="vulnerability",
        description="SHA1 used for security purposes (weak hash)",
        recommendation="Use SHA-256 or stronger hash functions",
    ),
    Pattern(
        name="ECB Mode Encryption",
        pattern=re.compile(
            r'(?:MODE_ECB|AES\.new\([^)]*,\s*AES\.MODE_ECB)',
            re.IGNORECASE
        ),
        severity=Severity.HIGH,
        category="vulnerability",
        description="ECB mode encryption is insecure",
        recommendation="Use CBC, GCM, or other authenticated encryption modes",
    ),

    # Debug/Config Issues
    Pattern(
        name="Debug Mode Enabled",
        pattern=re.compile(
            r'(?:DEBUG|debug)\s*[=:]\s*(?:True|true|1|"true"|\'true\')',
            re.IGNORECASE
        ),
        severity=Severity.MEDIUM,
        category="vulnerability",
        description="Debug mode enabled in code",
        recommendation="Ensure DEBUG is False in production",
        exclude_if=re.compile(r'test|spec|example|\.test\.|_test\.', re.IGNORECASE),
    ),
    Pattern(
        name="Hardcoded IP Address",
        pattern=re.compile(
            r'(?:host|server|ip|address)\s*[=:]\s*["\'](?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2[0-9]|3[01])\.\d+\.\d+)["\']',
            re.IGNORECASE
        ),
        severity=Severity.LOW,
        category="vulnerability",
        description="Hardcoded internal IP address",
        recommendation="Use configuration files or environment variables",
    ),

    # Cors misconfiguration
    Pattern(
        name="Overly Permissive CORS",
        pattern=re.compile(
            r'(?:Access-Control-Allow-Origin|cors_origins?)\s*[=:]\s*["\']?\*["\']?',
            re.IGNORECASE
        ),
        severity=Severity.MEDIUM,
        category="vulnerability",
        description="CORS allows all origins",
        recommendation="Restrict CORS to specific trusted origins",
    ),

    # Disable SSL verification
    Pattern(
        name="SSL Verification Disabled",
        pattern=re.compile(
            r'verify\s*=\s*False|CERT_NONE|check_hostname\s*=\s*False',
            re.IGNORECASE
        ),
        severity=Severity.HIGH,
        category="vulnerability",
        description="SSL certificate verification disabled",
        recommendation="Enable SSL verification to prevent MITM attacks",
    ),
]


# =============================================================================
# Pattern Groups
# =============================================================================

ALL_PATTERNS = SECRET_PATTERNS + MALWARE_PATTERNS + VULNERABILITY_PATTERNS

def get_patterns_by_category(category: str) -> list[Pattern]:
    """Get patterns for a specific category."""
    if category == "secret":
        return SECRET_PATTERNS
    elif category == "malware":
        return MALWARE_PATTERNS
    elif category == "vulnerability":
        return VULNERABILITY_PATTERNS
    else:
        return ALL_PATTERNS
