"""Tests for sandbox filesystem, shell, and safety metadata."""

from pathlib import Path

import pytest

from adk_loop_lab.tools.filesystem import SandboxFilesystem
from adk_loop_lab.tools.safety import TOOL_SPECS, SideEffectLevel
from adk_loop_lab.tools.shell import SandboxShell


class TestSandboxFilesystem:
    def test_read_write_exists_and_list_dir(self, tmp_path: Path) -> None:
        fs = SandboxFilesystem(str(tmp_path))

        fs.write("nested/example.txt", "hello")

        assert fs.exists("nested/example.txt")
        assert fs.read("nested/example.txt") == "hello"
        assert fs.list_dir("nested") == ["example.txt"]

    def test_resolve_rejects_path_traversal(self, tmp_path: Path) -> None:
        fs = SandboxFilesystem(str(tmp_path))

        with pytest.raises(ValueError, match="Path traversal rejected"):
            fs._resolve("../etc/passwd")


class TestSandboxShell:
    def test_rejects_non_allowlisted_command(self, tmp_path: Path) -> None:
        shell = SandboxShell(str(tmp_path))

        with pytest.raises(ValueError, match="Command not allowlisted"):
            shell.run("echo hello")

    def test_rejects_path_traversal_argument(self, tmp_path: Path) -> None:
        shell = SandboxShell(str(tmp_path))

        with pytest.raises(ValueError, match="Path traversal rejected"):
            shell.run("cat ../outside.txt")

    def test_runs_allowlisted_command(self, tmp_path: Path) -> None:
        (tmp_path / "sample.txt").write_text("content", encoding="utf-8")
        shell = SandboxShell(str(tmp_path))

        exit_code, stdout, stderr = shell.run("cat sample.txt")

        assert exit_code == 0
        assert stdout == "content"
        assert stderr == ""

    def test_enforces_timeout(self, tmp_path: Path) -> None:
        shell = SandboxShell(str(tmp_path))

        with pytest.raises(TimeoutError, match="timed out"):
            shell.run("python3 -c 'import time; time.sleep(2)'", timeout=1)

    def test_caps_output(self, tmp_path: Path) -> None:
        shell = SandboxShell(str(tmp_path))

        exit_code, stdout, stderr = shell.run(
            "python3 -c 'print(\"x\" * 200)'",
            max_output_bytes=80,
        )

        assert exit_code == 0
        assert len((stdout + stderr).encode("utf-8")) <= 80
        assert "truncated" in stderr


class TestToolSpecs:
    def test_side_effects_are_defined(self) -> None:
        assert TOOL_SPECS["read_file"].side_effect == SideEffectLevel.READ_ONLY
        assert TOOL_SPECS["write_file"].side_effect == SideEffectLevel.REVERSIBLE_WRITE
        assert TOOL_SPECS["run_shell"].side_effect == SideEffectLevel.EXECUTION
        assert TOOL_SPECS["run_tests"].timeout_seconds == 120
