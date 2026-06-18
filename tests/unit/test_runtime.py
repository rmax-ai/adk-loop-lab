"""Tests for state store, event recorder, and console formatter."""

import asyncio
import json
from pathlib import Path

import pytest

from adk_loop_lab.events.console import (
    format_decision,
    format_evaluation_line,
    format_iteration_header,
)
from adk_loop_lab.events.recorder import EventRecorder
from adk_loop_lab.models import (
    BudgetState,
    Decision,
    EvaluationResult,
    EvaluatorStatus,
    EventType,
    LoopEvent,
    LoopRun,
    LoopState,
    Phase,
)
from adk_loop_lab.state.sqlite import SqliteStateStore


@pytest.fixture
async def store() -> SqliteStateStore:
    s = SqliteStateStore(":memory:")
    await s.initialize()
    return s


@pytest.fixture
def run() -> LoopRun:
    return LoopRun(example_id="level-1", goal="test goal")


@pytest.fixture
def state() -> LoopState:
    return LoopState(phase=Phase.EXECUTE, progress_score=0.42)


# ── SqliteStateStore ─────────────────────────────────────────────────


class TestSqliteStateStore:
    async def test_save_and_load_run(self, store: SqliteStateStore, run: LoopRun) -> None:
        await store.save_run(run)
        loaded = await store.get_run(run.run_id)
        assert loaded is not None
        assert loaded.goal == run.goal
        assert loaded.example_id == run.example_id

    async def test_save_and_load_state(self, store: SqliteStateStore, run: LoopRun, state: LoopState) -> None:
        await store.save_run(run)
        await store.save_state(run.run_id, state)
        loaded = await store.get_state(run.run_id)
        assert loaded is not None
        assert loaded.phase == Phase.EXECUTE
        assert loaded.progress_score == 0.42

    async def test_list_runs_by_example(self, store: SqliteStateStore) -> None:
        r1 = LoopRun(example_id="level-1", goal="a")
        r2 = LoopRun(example_id="level-1", goal="b")
        r3 = LoopRun(example_id="level-2", goal="c")
        for r in [r1, r2, r3]:
            await store.save_run(r)

        level1 = await store.list_runs(example_id="level-1")
        assert len(level1) == 2

        all_runs = await store.list_runs()
        assert len(all_runs) == 3

    async def test_upsert_run(self, store: SqliteStateStore, run: LoopRun) -> None:
        await store.save_run(run)
        run.goal = "updated goal"
        await store.save_run(run)
        loaded = await store.get_run(run.run_id)
        assert loaded is not None
        assert loaded.goal == "updated goal"

    async def test_get_nonexistent(self, store: SqliteStateStore) -> None:
        assert await store.get_run("nonexistent") is None
        assert await store.get_state("nonexistent") is None

    async def test_close(self, store: SqliteStateStore, run: LoopRun) -> None:
        await store.save_run(run)
        await store.close()
        # Second close should be safe
        await store.close()


# ── EventRecorder ──────────────────────────────────────────────────────


class TestEventRecorder:
    def test_record_and_read(self, tmp_path: Path) -> None:
        recorder = EventRecorder(base_dir=str(tmp_path))
        event = LoopEvent(run_id="r1", iteration=1, event_type=EventType.RUN_STARTED)
        recorder.record(event)

        events = recorder.get_events("r1")
        assert len(events) == 1
        assert events[0].event_type == EventType.RUN_STARTED

    def test_multiple_events(self, tmp_path: Path) -> None:
        recorder = EventRecorder(base_dir=str(tmp_path))
        for i in range(5):
            recorder.record(LoopEvent(run_id="r1", iteration=i, event_type=EventType.ITERATION_STARTED))

        events = recorder.get_events("r1")
        assert len(events) == 5

    def test_jsonl_format(self, tmp_path: Path) -> None:
        recorder = EventRecorder(base_dir=str(tmp_path))
        event = LoopEvent(run_id="r1", iteration=1, event_type=EventType.STOP_DECISION)
        recorder.record(event)

        filepath = tmp_path / "r1" / "events.jsonl"
        lines = filepath.read_text().strip().split("\n")
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["event_type"] == "STOP_DECISION"

    def test_nonexistent_run(self, tmp_path: Path) -> None:
        recorder = EventRecorder(base_dir=str(tmp_path))
        events = recorder.get_events("nonexistent")
        assert events == []


# ── Console Formatter ──────────────────────────────────────────────────


class TestConsoleFormatter:
    def test_iteration_header(self) -> None:
        run = LoopRun(example_id="test", goal="g", max_iterations=6)
        state = LoopState(phase=Phase.VERIFY)
        budget = BudgetState(iteration=3, model_calls=7, tool_calls=2)

        header = format_iteration_header(run, state, budget)
        assert "test" in header or run.run_id[:8] in header
        assert "ITERATION" in header
        assert "VERIFY" in header

    def test_evaluation_line_pass(self) -> None:
        result = EvaluationResult(evaluator_name="unit_tests", status=EvaluatorStatus.PASS, score=1.0)
        line = format_evaluation_line(result)
        assert "unit_tests" in line

    def test_evaluation_line_fail(self) -> None:
        result = EvaluationResult(
            evaluator_name="lint",
            status=EvaluatorStatus.FAIL,
            score=0.0,
            failures=["E501 line too long"],
            summary="Lint failed",
        )
        line = format_evaluation_line(result)
        assert "lint" in line

    def test_decision_continue(self) -> None:
        output = format_decision(Decision.CONTINUE, "next: fix tests")
        assert "CONTINUE" in output
        assert "fix tests" in output

    def test_decision_success(self) -> None:
        output = format_decision(Decision.SUCCESS)
        assert "SUCCESS" in output
