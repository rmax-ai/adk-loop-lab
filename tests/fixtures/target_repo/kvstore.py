"""Simple in-memory key-value store.

This is a fixture target repository for the coding loop example.
The task: add expiration/TTL support while preserving backward compatibility.
"""

from typing import Any


class KVStore:
    """Simple in-memory key-value store."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        """Set a key-value pair."""
        self._data[key] = value

    def get(self, key: str) -> Any | None:
        """Get a value by key. Returns None if key not found."""
        return self._data.get(key)

    def delete(self, key: str) -> bool:
        """Delete a key. Returns True if key existed."""
        if key in self._data:
            del self._data[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if a key exists."""
        return key in self._data

    def keys(self) -> list[str]:
        """Return all keys."""
        return list(self._data.keys())

    def clear(self) -> None:
        """Remove all entries."""
        self._data.clear()
