"""Sandboxed filesystem operations."""

from pathlib import Path


class SandboxFilesystem:
    """Confined filesystem operations within a sandbox directory."""

    def __init__(self, sandbox_dir: str) -> None:
        self._root = Path(sandbox_dir).resolve()

    def _resolve(self, path: str) -> Path:
        """Resolve a path and verify it's within the sandbox."""
        resolved = (self._root / path).resolve()
        if self._root not in resolved.parents and resolved != self._root:
            raise ValueError(f"Path traversal rejected: {path}")
        return resolved

    def read(self, path: str) -> str:
        """Read a file within the sandbox."""
        target = self._resolve(path)
        return target.read_text(encoding="utf-8")

    def write(self, path: str, content: str) -> None:
        """Write a file within the sandbox."""
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def list_dir(self, path: str = ".") -> list[str]:
        """List directory contents."""
        target = self._resolve(path)
        return sorted(item.name for item in target.iterdir())

    def exists(self, path: str) -> bool:
        """Check if a path exists."""
        target = self._resolve(path)
        return target.exists()
