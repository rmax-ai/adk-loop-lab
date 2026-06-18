"""Tests for loop controller, lifecycle, and recovery."""

import asyncio

import pytest

from adk_loop_lab.events.recorder import EventRecorder
from adk_loop_lab.loop.controller import LoopController
from adk_loop_lab.loop.lifecycle import (
    PHASE_ORDER,
    TERMINAL_DECISIONS,
    is_terminal,
    next_phase,
    phase_index,
)
from adk_loop_lab.loop.recovery import FailureType, RecoveryPolicy
from adk_loop_lab.models import (
    BudgetConfig,
    Decision,
    EventType,
    LoopRun,
    LoopState,
    Phase,
    RunStatus,
)
from adk_loop_lab.state.sqlite import SqliteStateStore


# ── Lifecycle ────────────────────────────────────────────────────────


class TestLifecycle:
    def test_next_phase_forward(self) -> None:
        assert next_phase(Phase.DISCOVER) == Phase.PLAN
        assert next_phase(Phase.PLAN) == Phase.EXECUTE
        assert next_phase(Phase.EXECUTE) == Phase.VERIFY
        assert next_phase(Phase.VERIFY) == Phase.COMMIT
        assert next_phase(Phase.COMMIT) == Phase.REFLECT
        assert next_phase(Phase.REFLECT) == Phase.DECIDE

    def test_next_phase_loops(self) -> None:
        assert next_phase(Phase.DECIDE) == Phase.DISCOVER

    def test_phase_order_length(self) -> None:
        assert len(PHASE_ORDER) == 7

    def test_phase_index(self) -> None:
        assert phase_index(Phase.DISCOVER) == 0
        assert phase_index(Phase.DECIDE) == 6

    def test_terminal_decisions(self) -> None:
        assert is_terminal(Decision.SUCCESS)
        assert is_terminal(Decision.FAILED)
        assert is_terminal(Decision.BLOCKED)
        assert is_terminal(Decision.ESCALATE)
        assert is_terminal(Decision.BUDGET_EXHAUSTED)
        assert is_terminal(Decision.STAGNATED)

    def test_continue_is_not_terminal(self) -> None:
        assert not is_terminal(Decision.CONTINUE)

    def test_all_terminal_in_set(self) -> None:
        for d in Decision:
            if d != Decision.CONTINUE:
                assert d in TERMINAL_DECISIONS


# ── RecoveryPolicy ────────────────────────────────────────────────────


class TestRecoveryPolicy:
    def test_retries_transient(self) -> None:
        rp = RecoveryPolicy()
        assert rp.should_retry(FailureType.MODEL_TIMEOUT)
        assert rp.should_retry(FailureType.MALFORMED_OUTPUT)
        assert rp.should_retry(FailureType.STATE_STORE_FAILURE)

    def test_no_retry_deterministic(self) -> None:
        rp = RecoveryPolicy()
        assert not rp.should_retry(FailureType.TOOL_FAILURE)
        assert not rp.should_retry(FailureType.EVALUATOR_ERROR)

    async def test_with_recovery_success(self) -> None:
        rp = RecoveryPolicy(max_attempts=3, backoff_seconds=0.01)
        call_count = 0

        async def flaky() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("transient")
            return "ok"

        result = await rp.with_recovery("test", flaky, failure_type=FailureType.MODEL_TIMEOUT)
        assert result == "ok"
        assert call_count == 2

    async def test_with_recovery_exhausted(self) -> None:
        rp = RecoveryPolicy(max_attempts=2, backoff_seconds=0.01)

        async def always_fails() -> str:
            raise RuntimeError("persistent")

        with pytest.raises(RuntimeError, match="failed after 2 attempt"):
            await rp.with_recovery("test", always_fails, failure_type=FailureType.MODEL_TIMEOUT)


# ── LoopController ────────────────────────────────────────────────────


@pytest.fixture
async def controller() -> LoopController:
    store = SqliteStateStore(":memory:")
    await store.initialize()
    recorder = EventRecorder()
    return LoopController(store, recorder)


class TestLoopController:
    async def test_offline_run_completes(self, controller: LoopController) -> None:
        run = LoopRun(
            example_id="test",
            goal="verify controller",
            budgets=BudgetConfig(max_iterations=2, max_model_calls=10),
        )
        state = LoopState()

        final_run, final_state = await controller.run(run, state)
        assert final_run.current_iteration >= 1
        assert final_run.last_decision is not None

    async def test_budget_exhaustion_stops(self, controller: LoopController) -> None:
        run = LoopRun(
            example_id="test",
            goal="budget test",
            budgets=BudgetConfig(max_iterations=1),
        )
        state = LoopState()

        final_run, _ = await controller.run(run, state)
        assert final_run.last_decision == Decision.BUDGET_EXHAUSTED

    async def test_events_recorded(self, controller: LoopController) -> None:
        run = LoopRun(
            example_id="test",
            goal="event test",
            budgets=BudgetConfig(max_iterations=2),
        )
        state = LoopState()

        final_run, _ = await controller.run(run, state)
        recorder = controller._recorder
        events = recorder.get_events(final_run.run_id)
        assert len(events) > 0

        # Check for key event types
        event_types = {e.event_type for e in events}
        assert EventType.RUN_STARTED in event_types
        assert EventType.RUN_COMPLETED in event_types

    async def test_stagnation_tracking(self, controller: LoopController) -> None:
        """In offline mode with no evaluators, progress stays at 0 → stagnation accumulates."""
        run = LoopRun(
            example_id="test",
            goal="stagnation test",
            budgets=BudgetConfig(max_iterations=5, stagnation_threshold=2),
        )
        state = LoopState(progress_score=0.0)

        final_run, final_state = await controller.run(run, state)
        # In offline mode, progress stays at 0, stagnation_count will grow
        assert final_state.stagnation_count >= 2

    async def test_resume_from_checkpoint(self, controller: LoopController) -> None:
        """Run a short loop, then simulate interruption and resume."""
        run = LoopRun(
            example_id="test",
            goal="resume test",
            budgets=BudgetConfig(max_iterations=2),
        )
        state = LoopState()

        await controller.run(run, state)

        # Simulate interruption by marking the stored run as INTERRUPTED
        stored = await controller._store.get_run(run.run_id)
        assert stored is not None
        stored.status = RunStatus.INTERRUPTED
        await controller._store.save_run(stored)

        # Resume — controller will load checkpoint and re-run
        result = await controller.resume(run.run_id)
        assert result is not None
        resumed_run, resumed_state = result
        # After resume + re-run, the run has a terminal status
        assert resumed_run.last_decision is not None
