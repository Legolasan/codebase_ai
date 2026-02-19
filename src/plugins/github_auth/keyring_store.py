"""Secure token storage using system keyring.

The system keyring provides OS-level encryption:
- macOS: Keychain
- Windows: Windows Credential Manager
- Linux: Secret Service (GNOME Keyring, KWallet)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Keyring service identifiers
KEYRING_SERVICE = "assistant-github"
KEYRING_USERNAME = "github-token"


def _get_keyring():
    """Get the keyring module, importing lazily."""
    try:
        import keyring
        return keyring
    except ImportError:
        return None


def is_available() -> bool:
    """Check if keyring is available.

    Returns:
        True if keyring package is installed
    """
    return _get_keyring() is not None


def store_token(token: str) -> bool:
    """Store a GitHub token in the system keyring.

    The token is encrypted by the OS-level keyring service.

    Args:
        token: GitHub personal access token to store

    Returns:
        True if storage was successful

    Raises:
        RuntimeError: If keyring is not available
    """
    keyring = _get_keyring()
    if keyring is None:
        raise RuntimeError(
            "keyring package not installed. "
            "Install with: pip install keyring"
        )

    try:
        keyring.set_password(KEYRING_SERVICE, KEYRING_USERNAME, token)
        logger.info("Token stored in system keyring")
        return True
    except Exception as e:
        logger.error(f"Failed to store token: {e}")
        raise RuntimeError(f"Failed to store token: {e}")


def get_token() -> Optional[str]:
    """Retrieve the GitHub token from the system keyring.

    Returns:
        The stored token, or None if not found
    """
    keyring = _get_keyring()
    if keyring is None:
        return None

    try:
        return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME)
    except Exception as e:
        logger.debug(f"Failed to retrieve token: {e}")
        return None


def delete_token() -> bool:
    """Remove the GitHub token from the system keyring.

    Returns:
        True if deletion was successful or token didn't exist
    """
    keyring = _get_keyring()
    if keyring is None:
        return True  # Nothing to delete

    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USERNAME)
        logger.info("Token removed from system keyring")
        return True
    except keyring.errors.PasswordDeleteError:
        # Token didn't exist
        return True
    except Exception as e:
        logger.error(f"Failed to delete token: {e}")
        return False


def has_token() -> bool:
    """Check if a token is stored in the keyring.

    Returns:
        True if a token exists
    """
    return get_token() is not None


def get_keyring_info() -> dict:
    """Get information about the keyring backend.

    Returns:
        Dict with keyring status and backend info
    """
    keyring = _get_keyring()
    if keyring is None:
        return {
            "available": False,
            "backend": None,
            "error": "keyring package not installed",
        }

    try:
        backend = keyring.get_keyring()
        return {
            "available": True,
            "backend": type(backend).__name__,
            "has_token": has_token(),
        }
    except Exception as e:
        return {
            "available": False,
            "backend": None,
            "error": str(e),
        }
