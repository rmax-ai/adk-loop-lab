"""Configuration loading for adk-loop-lab."""

from __future__ import annotations

import os
from pathlib import Path

_DOTENV_LOADED = False


def _load_dotenv() -> None:
    """Load a local .env file into the environment if present."""
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return

    dotenv_path = Path.cwd() / ".env"
    if dotenv_path.exists():
        for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", maxsplit=1)
            os.environ.setdefault(key.strip(), value.strip())

    _DOTENV_LOADED = True


def get_api_key() -> str | None:
    """Get the Gemini API key from environment."""
    _load_dotenv()
    return os.environ.get("GOOGLE_API_KEY")


def get_state_dir() -> str:
    """Get the state directory root."""
    _load_dotenv()
    return os.environ.get("ADK_LOOP_STATE_DIR", "var")


def get_model_name() -> str:
    """Get the default Gemini model name."""
    _load_dotenv()
    return os.environ.get("GOOGLE_MODEL", "gemini-3-flash-preview")
