"""ADK version compatibility layer.

Isolates version-specific APIs and deprecation handling.
"""

from __future__ import annotations

import importlib.metadata
import logging

logger = logging.getLogger(__name__)

MIN_ADK_VERSION = (2, 2, 0)


def check_adk_version() -> tuple[int, int, int]:
    """Return the installed ADK version as ``(major, minor, patch)``."""
    version_str: str
    try:
        from google.adk import __version__ as version_str
    except ImportError:
        try:
            version_str = importlib.metadata.version("google-adk")
        except importlib.metadata.PackageNotFoundError:
            logger.warning("cannot_detect_adk_version")
            return (0, 0, 0)

    parts = version_str.split(".")
    major = int(parts[0])
    minor = int(parts[1]) if len(parts) > 1 else 0
    patch_str = parts[2] if len(parts) > 2 else "0"
    patch = int("".join(char for char in patch_str if char.isdigit()) or "0")
    return (major, minor, patch)


def require_adk_version(min_version: tuple[int, int, int] = MIN_ADK_VERSION) -> None:
    """Raise ``RuntimeError`` if the installed ADK version is too old."""
    current = check_adk_version()
    if current < min_version:
        current_str = ".".join(map(str, current))
        minimum_str = ".".join(map(str, min_version))
        raise RuntimeError(f"ADK version {current_str} is below minimum required {minimum_str}")


def get_default_model() -> str:
    """Return the recommended default model for ADK agents."""
    return "gemini-3-flash-preview"
