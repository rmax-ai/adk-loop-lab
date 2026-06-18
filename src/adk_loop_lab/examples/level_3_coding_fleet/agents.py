"""Agents for the multi-agent coding example."""

from __future__ import annotations

from google.adk.agents.llm_agent import LlmAgent

from adk_loop_lab.adk.agents import create_agent
from adk_loop_lab.adk.fake_model import FakeModelScript

FAKE_SCRIPT = FakeModelScript()
_FAKE_RESPONSES: list[tuple[str, str]] = []


def _register_fake_response(prompt_fragment: str, response: str) -> None:
    _FAKE_RESPONSES.append((prompt_fragment, response))
    FAKE_SCRIPT.add(prompt_fragment, response)


def get_fake_response(prompt: str) -> str:
    """Return a canned response for a matching prompt fragment."""
    for fragment, response in _FAKE_RESPONSES:
        if fragment in prompt:
            return response
    raise ValueError(f"No fake response registered for prompt: {prompt}")


def setup_fake_responses() -> None:
    """Register canned responses for deterministic testing."""
    if _FAKE_RESPONSES:
        return

    _register_fake_response(
        "investigate the repository",
        (
            '{"findings": [{"file": "kvstore.py", "issue": "set() only accepts key and '
            'value", "suggestion": "Add an optional ttl_seconds parameter and expire '
            'entries lazily"}], "tests_present": true, "recommended_files": '
            '["kvstore.py", "tests/test_kvstore.py"]}'
        ),
    )
    _register_fake_response(
        "plan the next bounded action",
        (
            '{"action": "add_ttl_parameter", "files": ["kvstore.py", "tests/test_kvstore.py"], '
            '"description": "Add an optional ttl_seconds parameter to set(), store expiry '
            "metadata, expire keys lazily in get()/exists()/keys(), and add backward "
            'compatibility and expiration tests."}'
        ),
    )
    _register_fake_response(
        "implement the change",
        """```python
from __future__ import annotations

import time
from typing import Any


class KVStore:
    \"\"\"Simple in-memory key-value store.\"\"\"

    def __init__(self) -> None:
        self._data: dict[str, tuple[Any, float | None]] = {}

    def _is_expired(self, key: str, now: float | None = None) -> bool:
        entry = self._data.get(key)
        if entry is None:
            return False

        _, expires_at = entry
        if expires_at is None:
            return False

        current_time = time.time() if now is None else now
        if current_time < expires_at:
            return False

        del self._data[key]
        return True

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        \"\"\"Set a key-value pair with optional TTL in seconds.\"\"\"
        expires_at = None
        if ttl_seconds is not None:
            expires_at = time.time() + ttl_seconds
        self._data[key] = (value, expires_at)

    def get(self, key: str) -> Any | None:
        \"\"\"Get a value by key. Returns None if key not found or expired.\"\"\"
        if self._is_expired(key):
            return None

        entry = self._data.get(key)
        if entry is None:
            return None
        return entry[0]

    def delete(self, key: str) -> bool:
        \"\"\"Delete a key. Returns True if key existed.\"\"\"
        if self._is_expired(key):
            return False
        if key in self._data:
            del self._data[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        \"\"\"Check if a key exists and is not expired.\"\"\"
        if self._is_expired(key):
            return False
        return key in self._data

    def keys(self) -> list[str]:
        \"\"\"Return all non-expired keys.\"\"\"
        for key in list(self._data):
            self._is_expired(key)
        return list(self._data.keys())

    def clear(self) -> None:
        \"\"\"Remove all entries.\"\"\"
        self._data.clear()
```""",
    )
    _register_fake_response(
        "design tests",
        (
            "Add tests for TTL expiration after a short delay, backward-compatible "
            "set(key, value), and ensuring expired keys are removed from exists() and keys()."
        ),
    )


def create_observer_agent(*, model: str | None = None) -> LlmAgent:
    """Create the repository observer agent."""
    return create_agent(
        name="observer",
        model=model,
        instruction=(
            "You are a code repository observer. Inspect the given repository and "
            "report current file structure, existing tests, and issues relevant to "
            "the task."
        ),
    )


def create_planner_agent(*, model: str | None = None) -> LlmAgent:
    """Create the bounded-action planner agent."""
    return create_agent(
        name="planner",
        model=model,
        instruction=(
            "You are a task planner. Given a coding task and repository state, "
            "propose exactly one bounded action. Return JSON with keys action, "
            "files, and description."
        ),
    )


def create_implementer_agent(*, model: str | None = None) -> LlmAgent:
    """Create the implementation agent."""
    return create_agent(
        name="implementer",
        model=model,
        instruction=(
            "You are a careful implementation agent. Given a specific task, "
            "produce the exact code changes needed. Show the full updated file in "
            "a Python markdown block and do not modify unrelated code."
        ),
    )
