"""Allowlisted shell execution with safety constraints."""

from __future__ import annotations

import shlex
import subprocess
from enum import Enum
from pathlib import Path


class ToolCategory(Enum):
    """Shell tool effect categories."""

    READ_ONLY = "READ_ONLY"
    REVERSIBLE_WRITE = "REVERSIBLE_WRITE"
    IRREVERSIBLE_WRITE = "IRREVERSIBLE_WRITE"
    EXECUTION = "EXECUTION"


ALLOWED_COMMANDS = {
    "python3",
    "python",
    "pytest",
    "cat",
    "ls",
    "find",
    "grep",
    "wc",
    "head",
    "tail",
    "diff",
    "patch",
    "git",
}

_MINIMAL_ENV = {
    "HOME": "/nonexistent",
    "PATH": "/usr/bin:/bin",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
}


class SandboxShell:
    """Shell executor confined to a sandbox directory with allowlisted commands."""

    def __init__(self, sandbox_dir: str, allow_network: bool = False) -> None:
        self._sandbox_dir = Path(sandbox_dir).resolve()
        self._allow_network = allow_network

    def run(
        self,
        command: str,
        timeout: int = 30,
        max_output_bytes: int = 100_000,
    ) -> tuple[int, str, str]:
        """Run a shell command in the sandbox."""
        argv = shlex.split(command)
        if not argv:
            raise ValueError("Command must not be empty.")

        self._validate_command(argv)

        env = None if self._allow_network else dict(_MINIMAL_ENV)
        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                cwd=self._sandbox_dir,
                env=env,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TimeoutError(f"Command timed out after {timeout} seconds: {command}") from exc

        stdout, stderr = self._truncate_output(
            stdout=completed.stdout,
            stderr=completed.stderr,
            max_output_bytes=max_output_bytes,
        )
        return completed.returncode, stdout, stderr

    def _validate_command(self, argv: list[str]) -> None:
        """Validate command against allowlist and path constraints."""
        binary = argv[0]
        if binary not in ALLOWED_COMMANDS:
            raise ValueError(f"Command not allowlisted: {binary}")

        for arg in argv[1:]:
            self._validate_argument(arg)

    def _validate_argument(self, arg: str) -> None:
        if arg.startswith("-"):
            return

        parts = Path(arg).parts
        if ".." in parts:
            raise ValueError(f"Path traversal rejected: {arg}")

        if Path(arg).is_absolute():
            resolved = Path(arg).resolve()
            if self._sandbox_dir not in resolved.parents and resolved != self._sandbox_dir:
                raise ValueError(f"Absolute path outside sandbox rejected: {arg}")

    def _truncate_output(self, stdout: str, stderr: str, max_output_bytes: int) -> tuple[str, str]:
        combined = (stdout + stderr).encode("utf-8")
        if len(combined) <= max_output_bytes:
            return stdout, stderr

        warning = f"\n[output truncated to {max_output_bytes} bytes]"
        warning_bytes = warning.encode("utf-8")
        budget = max(max_output_bytes - len(warning_bytes), 0)
        stdout_bytes = stdout.encode("utf-8")
        stderr_bytes = stderr.encode("utf-8")
        kept_stdout = stdout_bytes[:budget]
        remaining_budget = max(budget - len(kept_stdout), 0)
        kept_stderr = stderr_bytes[:remaining_budget]

        truncated_stdout = kept_stdout.decode("utf-8", errors="ignore")
        truncated_stderr = kept_stderr.decode("utf-8", errors="ignore") + warning
        return truncated_stdout, truncated_stderr
