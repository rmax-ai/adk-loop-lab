from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

import pytest

from adk_loop_lab.events.recorder import EventRecorder
from adk_loop_lab.loop.checkpoints import CheckpointManager
from adk_loop_lab.loop.controller import LoopController
from adk_loop_lab.models import (
    BudgetConfig,
    Decision,
    EvaluationResult,
    EvaluatorStatus,
    EventType,
    LoopRun,
    LoopState,
    Phase,
    RunStatus,
)
from adk_loop_lab.state.sqlite import SqliteStateStore
from adk_loop_lab.tools.shell import SandboxShell

AgentFunc = Callable[[str, LoopState], Awaitable[str]]
EvaluatorFunc = Callable[[LoopState], Awaitable[EvaluationResult] | EvaluationResult]


async def _make_controller(
    tmp_path: Path,
    *,
    agent_func: AgentFunc | None = None,
) -> tuple[SqliteStateStore, EventRecorder, LoopController]:
    base_dir = tmp_path / "runs"
    store = SqliteStateStore(str(tmp_path / "state.db"))
    await store.initialize()
    recorder = EventRecorder(base_dir=str(base_dir))
    controller = LoopController(store, recorder, agent_func=agent_func)
    return store, recorder, controller


def _pass_result(name: str, score: float = 1.0) -> EvaluationResult:
    return EvaluationResult(
        evaluator_name=name,
        status=EvaluatorStatus.PASS,
        score=score,
        summary=f"{name} passed",
    )


def _fail_result(name: str, score: float = 0.0) -> EvaluationResult:
    return EvaluationResult(
        evaluator_name=name,
        status=EvaluatorStatus.FAIL,
        score=score,
        summary=f"{name} failed",
        failures=[f"{name} did not pass"],
    )


@pytest.mark.asyncio
async def test_controller_retries_transient_model_failure(tmp_path: Path) -> None:
    """Loop continues after one transient planner failure."""

    attempts = {"plan": 0}

    async def agent_func(_: str, state: LoopState) -> str:
        if state.phase is Phase.PLAN:
            attempts["plan"] += 1
            if attempts["plan"] == 1:
                raise RuntimeError("temporary planner outage")
            return "draft_ready"
        if state.phase is Phase.REFLECT:
            return "reflection"
        return ""

    _store, _recorder, controller = await _make_controller(tmp_path, agent_func=agent_func)
    run = LoopRun(
        example_id="failure_injection",
        goal="recover from a transient model error",
        budgets=BudgetConfig(max_iterations=3, max_model_calls=10, retry_backoff_seconds=0.0),
    )
    state = LoopState()

    final_run, final_state = await controller.run(
        run, state, evaluators=[lambda _: _pass_result("ok")]
    )

    assert attempts["plan"] == 2
    assert final_run.last_decision == Decision.SUCCESS
    assert final_run.status == RunStatus.COMPLETED
    assert "draft_ready" in final_state.pending_actions


@pytest.mark.asyncio
async def test_controller_stops_on_permanent_model_failure(tmp_path: Path) -> None:
    """Loop stops when planning fails repeatedly."""

    async def agent_func(_: str, state: LoopState) -> str:
        if state.phase is Phase.PLAN:
            raise RuntimeError("planner unavailable")
        return ""

    _store, recorder, controller = await _make_controller(tmp_path, agent_func=agent_func)
    run = LoopRun(
        example_id="failure_injection",
        goal="stop on unrecoverable model failure",
        budgets=BudgetConfig(max_iterations=3, retry_max_attempts=2, retry_backoff_seconds=0.0),
    )

    final_run, _final_state = await controller.run(run, LoopState())
    events = recorder.get_events(run.run_id)

    assert final_run.last_decision == Decision.FAILED
    assert final_run.status == RunStatus.FAILED
    assert EventType.RUN_FAILED in {event.event_type for event in events}


@pytest.mark.asyncio
async def test_controller_stops_on_tool_timeout(tmp_path: Path) -> None:
    """Loop fails when a sandboxed tool exceeds its timeout."""

    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir()
    shell = SandboxShell(str(sandbox_dir))

    async def agent_func(_: str, state: LoopState) -> str:
        if state.phase is Phase.PLAN:
            return "slow_tool"
        if state.phase is Phase.REFLECT:
            return "reflection"
        return ""

    def slow_tool() -> tuple[int, str, str]:
        return shell.run('python3 -c "import time; time.sleep(2)"', timeout=1)

    _store, recorder, controller = await _make_controller(tmp_path, agent_func=agent_func)
    run = LoopRun(
        example_id="failure_injection",
        goal="surface tool timeout",
        budgets=BudgetConfig(max_iterations=2, retry_backoff_seconds=0.0),
    )

    final_run, final_state = await controller.run(
        run,
        LoopState(),
        tools={"slow_tool": slow_tool},
        evaluators=[lambda _: _fail_result("pending")],
    )

    assert final_run.last_decision == Decision.FAILED
    assert final_run.status == RunStatus.FAILED
    assert final_state.completed_actions == []
    assert EventType.ERROR in {event.event_type for event in recorder.get_events(run.run_id)}


@pytest.mark.asyncio
async def test_max_iteration_budget_exhaustion_stops_loop(tmp_path: Path) -> None:
    """Loop stops exactly at the configured iteration budget."""

    _store, _recorder, controller = await _make_controller(tmp_path)
    run = LoopRun(
        example_id="failure_injection",
        goal="hit max iteration budget",
        budgets=BudgetConfig(max_iterations=3),
    )

    final_run, _final_state = await controller.run(run, LoopState())

    assert final_run.current_iteration == 3
    assert final_run.last_decision == Decision.BUDGET_EXHAUSTED


@pytest.mark.asyncio
async def test_max_model_call_budget_exhaustion_stops_loop(tmp_path: Path) -> None:
    """Loop stops when model-call budget is exhausted."""

    async def agent_func(_: str, state: LoopState) -> str:
        if state.phase is Phase.PLAN:
            return "draft"
        if state.phase is Phase.REFLECT:
            return "reflection"
        return ""

    _store, _recorder, controller = await _make_controller(tmp_path, agent_func=agent_func)
    run = LoopRun(
        example_id="failure_injection",
        goal="hit model-call budget",
        budgets=BudgetConfig(max_iterations=5, max_model_calls=1, retry_backoff_seconds=0.0),
    )

    final_run, _final_state = await controller.run(
        run,
        LoopState(),
        evaluators=[lambda _: _fail_result("not_done")],
    )

    assert final_run.current_iteration == 1
    assert final_run.last_decision == Decision.BUDGET_EXHAUSTED


@pytest.mark.asyncio
async def test_max_tool_call_budget_exhaustion_stops_loop(tmp_path: Path) -> None:
    """Loop stops when tool-call budget is exhausted."""

    async def agent_func(_: str, state: LoopState) -> str:
        if state.phase is Phase.PLAN:
            return "quick_tool"
        if state.phase is Phase.REFLECT:
            return "reflection"
        return ""

    def quick_tool() -> str:
        return "done"

    _store, _recorder, controller = await _make_controller(tmp_path, agent_func=agent_func)
    run = LoopRun(
        example_id="failure_injection",
        goal="hit tool-call budget",
        budgets=BudgetConfig(max_iterations=5, max_tool_calls=1, retry_backoff_seconds=0.0),
    )

    final_run, final_state = await controller.run(
        run,
        LoopState(),
        tools={"quick_tool": quick_tool},
        evaluators=[lambda _: _fail_result("not_done")],
    )

    assert final_run.current_iteration == 1
    assert final_run.last_decision == Decision.BUDGET_EXHAUSTED
    assert final_state.completed_actions == ["quick_tool"]


@pytest.mark.asyncio
async def test_corrupt_state_row_degrades_gracefully(tmp_path: Path) -> None:
    """Corrupt persisted state returns ``None`` instead of raising."""

    store = SqliteStateStore(str(tmp_path / "state.db"))
    await store.initialize()
    run = LoopRun(example_id="failure_injection", goal="persist state")
    state = LoopState()

    await store.save_run(run)
    await store.save_state(run.run_id, state)

    connection = store._require_connection()
    await connection.execute(
        "UPDATE loop_states SET data = ? WHERE run_id = ?",
        ("{not valid json", run.run_id),
    )
    await connection.commit()

    restored_state = await store.get_state(run.run_id)

    assert restored_state is None


@pytest.mark.asyncio
async def test_corrupt_latest_checkpoint_falls_back_to_previous_checkpoint(tmp_path: Path) -> None:
    """Resume uses the latest valid checkpoint when the newest row is corrupt."""

    store = SqliteStateStore(str(tmp_path / "state.db"))
    await store.initialize()
    recorder = EventRecorder(base_dir=str(tmp_path / "runs"))
    manager = CheckpointManager(store, recorder)
    run = LoopRun(example_id="failure_injection", goal="resume after checkpoint corruption")

    state = LoopState(progress_score=0.1)
    run.current_iteration = 1
    await manager.create_checkpoint(run, state)

    state.progress_score = 0.2
    run.current_iteration = 2
    await manager.create_checkpoint(run, state)

    connection = store._require_connection()
    await connection.execute(
        "UPDATE checkpoints SET state_data = ? WHERE checkpoint_id = ?",
        ("{broken", f"{run.run_id}:2"),
    )
    await connection.commit()

    resumed = await manager.resume_run(run.run_id)

    assert resumed is not None
    resumed_run, resumed_state = resumed
    assert resumed_run.current_iteration == 1
    assert resumed_state.progress_score == pytest.approx(0.1)


@pytest.mark.asyncio
async def test_stagnation_detection_stops_loop(tmp_path: Path) -> None:
    """Loop stops with ``STAGNATED`` after repeated non-improving iterations."""

    async def agent_func(_: str, state: LoopState) -> str:
        if state.phase is Phase.PLAN:
            return f"proposal-{state.facts.get('current_iteration', 0)}"
        if state.phase is Phase.REFLECT:
            return "no progress"
        return ""

    _store, _recorder, controller = await _make_controller(tmp_path, agent_func=agent_func)
    run = LoopRun(
        example_id="failure_injection",
        goal="detect stagnation",
        budgets=BudgetConfig(max_iterations=5, stagnation_threshold=2, retry_backoff_seconds=0.0),
    )

    final_run, final_state = await controller.run(
        run,
        LoopState(progress_score=0.0),
        evaluators=[lambda _: _fail_result("stalled", score=0.0)],
    )

    assert final_run.current_iteration == 2
    assert final_run.last_decision == Decision.STAGNATED
    assert final_state.stagnation_count == 2


@pytest.mark.asyncio
async def test_checkpoint_and_resume_after_simulated_crash(tmp_path: Path) -> None:
    """Loop resumes from the latest checkpoint after a mid-run crash."""

    crash_state = {"triggered": False}

    async def agent_func(_: str, state: LoopState) -> str:
        if state.phase is Phase.PLAN:
            return f"iteration-{state.facts.get('current_iteration', 0)}"
        if state.phase is Phase.REFLECT:
            return "reflection"
        return ""

    async def evaluator(state: LoopState) -> EvaluationResult:
        iteration = int(state.facts.get("current_iteration", 0))
        if iteration == 3 and not crash_state["triggered"]:
            crash_state["triggered"] = True
            raise RuntimeError("simulated crash during verification")
        if iteration >= 3:
            return _pass_result("complete")
        return _fail_result("keep_going", score=0.2)

    _store, _recorder, controller = await _make_controller(tmp_path, agent_func=agent_func)
    run = LoopRun(
        example_id="failure_injection",
        goal="resume from checkpoint",
        budgets=BudgetConfig(max_iterations=5, retry_backoff_seconds=0.0),
    )

    failed_run, _failed_state = await controller.run(run, LoopState(), evaluators=[evaluator])

    assert failed_run.status == RunStatus.FAILED
    assert failed_run.current_iteration == 3

    resumed = await controller.resume(run.run_id, evaluators=[evaluator])

    assert resumed is not None
    resumed_run, resumed_state = resumed
    assert resumed_run.status == RunStatus.COMPLETED
    assert resumed_run.current_iteration == 3
    assert resumed_run.last_decision == Decision.SUCCESS
    assert resumed_state.progress_score == pytest.approx(1.0)
