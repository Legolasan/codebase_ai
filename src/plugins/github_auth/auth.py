"""GitHub authentication strategies.

Provides multiple ways to authenticate with GitHub:
- Environment variable (GITHUB_TOKEN)
- System keyring (encrypted)
- gh CLI (GitHub CLI)
"""

import logging
import os
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AuthResult:
    """Result of an authentication attempt."""

    success: bool
    token: Optional[str] = None
    username: Optional[str] = None
    method: Optional[str] = None
    error: Optional[str] = None


class AuthStrategy(ABC):
    """Base class for authentication strategies."""

    name: str = "base"

    @abstractmethod
    def get_token(self) -> Optional[str]:
        """Attempt to get a GitHub token.

        Returns:
            Token string if available, None otherwise
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this strategy is available.

        Returns:
            True if the strategy can be used
        """
        pass


class EnvTokenStrategy(AuthStrategy):
    """Read token from GITHUB_TOKEN environment variable."""

    name = "env"

    def get_token(self) -> Optional[str]:
        """Get token from environment."""
        return os.environ.get("GITHUB_TOKEN")

    def is_available(self) -> bool:
        """Check if GITHUB_TOKEN is set."""
        return "GITHUB_TOKEN" in os.environ


class KeyringStrategy(AuthStrategy):
    """Read token from system keyring (encrypted by OS).

    Requires the 'keyring' package to be installed.
    """

    name = "keyring"
    SERVICE_NAME = "assistant-github"
    USERNAME = "github-token"

    def __init__(self):
        self._keyring = None

    def _get_keyring(self):
        """Lazy import of keyring module."""
        if self._keyring is None:
            try:
                import keyring
                self._keyring = keyring
            except ImportError:
                pass
        return self._keyring

    def get_token(self) -> Optional[str]:
        """Get token from keyring."""
        keyring = self._get_keyring()
        if keyring:
            try:
                return keyring.get_password(self.SERVICE_NAME, self.USERNAME)
            except Exception as e:
                logger.debug(f"Failed to get token from keyring: {e}")
        return None

    def is_available(self) -> bool:
        """Check if keyring is available and has a token."""
        return self.get_token() is not None


class GHCLIStrategy(AuthStrategy):
    """Use GitHub CLI (gh) for authentication.

    Requires gh to be installed and authenticated.
    """

    name = "gh_cli"

    def get_token(self) -> Optional[str]:
        """Get token from gh CLI."""
        try:
            result = subprocess.run(
                ["gh", "auth", "token"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.debug(f"Failed to get token from gh CLI: {e}")
        return None

    def is_available(self) -> bool:
        """Check if gh CLI is available and authenticated."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False


class GitHubAuth:
    """Facade for GitHub authentication.

    Tries multiple strategies in order:
    1. Environment variable (GITHUB_TOKEN)
    2. System keyring (encrypted)
    3. GitHub CLI (gh auth token)
    """

    def __init__(self):
        self.strategies: list[AuthStrategy] = [
            EnvTokenStrategy(),
            KeyringStrategy(),
            GHCLIStrategy(),
        ]

    def get_token(self) -> Optional[str]:
        """Get a GitHub token using the first available strategy.

        Returns:
            Token string if available, None otherwise
        """
        for strategy in self.strategies:
            token = strategy.get_token()
            if token:
                logger.debug(f"Got token from {strategy.name} strategy")
                return token
        return None

    def authenticate(self) -> AuthResult:
        """Authenticate with GitHub and return details.

        Returns:
            AuthResult with token and user info
        """
        for strategy in self.strategies:
            token = strategy.get_token()
            if token:
                # Verify token by getting user info
                username = self._get_username(token)
                if username:
                    return AuthResult(
                        success=True,
                        token=token,
                        username=username,
                        method=strategy.name,
                    )
                else:
                    logger.warning(f"Token from {strategy.name} appears invalid")

        return AuthResult(
            success=False,
            error="No valid GitHub authentication found",
        )

    def _get_username(self, token: str) -> Optional[str]:
        """Verify token and get username.

        Args:
            token: GitHub token to verify

        Returns:
            Username if token is valid, None otherwise
        """
        try:
            import httpx

            response = httpx.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
                timeout=10,
            )
            if response.status_code == 200:
                return response.json().get("login")
        except Exception as e:
            logger.debug(f"Failed to verify token: {e}")
        return None

    def get_auth_status(self) -> dict:
        """Get detailed authentication status.

        Returns:
            Dict with status of each strategy
        """
        status = {
            "authenticated": False,
            "method": None,
            "username": None,
            "strategies": {},
        }

        for strategy in self.strategies:
            strategy_status = {
                "available": strategy.is_available(),
                "has_token": strategy.get_token() is not None,
            }
            status["strategies"][strategy.name] = strategy_status

        # Try to authenticate
        result = self.authenticate()
        if result.success:
            status["authenticated"] = True
            status["method"] = result.method
            status["username"] = result.username

        return status

    def get_headers(self) -> dict:
        """Get HTTP headers for authenticated requests.

        Returns:
            Dict with Authorization header if token available
        """
        token = self.get_token()
        if token:
            return {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            }
        return {"Accept": "application/vnd.github+json"}

    def configure_git_credentials(self) -> bool:
        """Configure git to use the token for HTTPS.

        Returns:
            True if configuration was successful
        """
        token = self.get_token()
        if not token:
            return False

        try:
            # Configure git credential helper
            subprocess.run(
                [
                    "git",
                    "config",
                    "--global",
                    "credential.helper",
                    "cache --timeout=3600",
                ],
                check=True,
            )
            logger.info("Configured git credential caching")
            return True
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to configure git credentials: {e}")
            return False
