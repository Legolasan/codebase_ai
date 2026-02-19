"""GitHub authentication plugin.

This plugin provides secure GitHub authentication with multiple
strategies (env vars, keyring, gh CLI) and enhanced git operations.
"""

from .plugin import GitHubAuthPlugin

__all__ = ["GitHubAuthPlugin"]
