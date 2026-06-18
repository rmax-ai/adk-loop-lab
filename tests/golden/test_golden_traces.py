from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import pytest

from adk_loop_lab.events.recorder import EventRecorder
from adk_loop_lab.examples.level_1_refinement.example import run_example as run_level_1_example
from adk_loop_lab.examples.level_2_research.example import run_example as run_level_2_example
from adk_loop_lab.examples.level_3_coding_fleet.example import run_example as run_level_3_example
from adk_loop_lab.models import LoopRun, LoopState

ExampleRunner = Callable[..., Awaitable[tuple[LoopRun, LoopState]]]

_UPDATE_GOLDEN_ENV = "ADK_LOOP_LAB_UPDATE_GOLDEN"
_TRACES_DIR = Path(__file__).parent / "traces"


def _should_update_golden() -> bool:
    return os.environ.get(_UPDATE_GOLDEN_ENV, "").lower() in {"1", "true", "yes", "on"}


def _normalize_trace(base_dir: Path, run_id: str) -> list[dict[str, Any]]:
    recorder = EventRecorder(base_dir=str(base_dir))
    normalized: list[dict[str, Any]] = []
    for event in recorder.get_events(run_id):
        normalized.append(
            {
                "event_type": event.event_type.value,
                "actor": event.actor,
                "iteration": event.iteration,
                "phase": event.payload.get("phase"),
            }
        )
    return normalized


def _load_golden(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []

    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _write_golden(path: Path, trace: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(item, sort_keys=True) for item in trace)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")


async def _assert_golden_trace(
    tmp_path: Path,
    *,
    runner: ExampleRunner,
    golden_path: Path,
) -> None:
    base_dir = tmp_path / "runs"
    db_path = tmp_path / "state.db"
    run, _state = await runner(
        use_fake_model=True,
        base_dir=str(base_dir),
        db_path=str(db_path),
    )
    actual = _normalize_trace(base_dir, run.run_id)
    expected = _load_golden(golden_path)

    if _should_update_golden() or not expected:
        _write_golden(golden_path, actual)
        expected = _load_golden(golden_path)

    assert actual == expected


@pytest.mark.asyncio
async def test_level_1_golden_trace_matches(tmp_path: Path) -> None:
    """Level 1 refinement produces the expected event sequence."""

    await _assert_golden_trace(
        tmp_path,
        runner=run_level_1_example,
        golden_path=_TRACES_DIR / "level_1_trace.jsonl",
    )


@pytest.mark.asyncio
async def test_level_2_golden_trace_matches(tmp_path: Path) -> None:
    """Level 2 research produces the expected event sequence."""

    await _assert_golden_trace(
        tmp_path,
        runner=run_level_2_example,
        golden_path=_TRACES_DIR / "level_2_trace.jsonl",
    )


@pytest.mark.asyncio
async def test_level_3_golden_trace_matches(tmp_path: Path) -> None:
    """Level 3 coding produces the expected event sequence."""

    await _assert_golden_trace(
        tmp_path,
        runner=run_level_3_example,
        golden_path=_TRACES_DIR / "level_3_trace.jsonl",
    )
