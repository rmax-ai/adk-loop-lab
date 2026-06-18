"""Tests for CLI and configuration helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from adk_loop_lab import config
from adk_loop_lab.cli import main


class TestConfig:
    def test_getters_read_dotenv(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".env").write_text(
            "\n".join(
                [
                    "GOOGLE_API_KEY=test-key",
                    "ADK_LOOP_STATE_DIR=tmp-var",
                    "GOOGLE_MODEL=gemini-test-model",
                ]
            ),
            encoding="utf-8",
        )
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("ADK_LOOP_STATE_DIR", raising=False)
        monkeypatch.delenv("GOOGLE_MODEL", raising=False)
        monkeypatch.setattr(config, "_DOTENV_LOADED", False)

        assert config.get_api_key() == "test-key"
        assert config.get_state_dir() == "tmp-var"
        assert config.get_model_name() == "gemini-test-model"


class TestCli:
    def test_examples_lists_examples(self) -> None:
        runner = CliRunner()

        result = runner.invoke(main, ["examples"])

        assert result.exit_code == 0
        assert "level-1" in result.output
        assert "level-2" in result.output
        assert "level-3" in result.output

    def test_run_rejects_unknown_example(self) -> None:
        runner = CliRunner()

        result = runner.invoke(main, ["run", "unknown"])

        assert result.exit_code == 1
        assert "Unknown example" in result.output
