"""Tests for transactions, checkpoints, and budget/stopping policies."""

import pytest

from adk_loop_lab.events.recorder import EventRecorder
from adk_loop_lab.loop.checkpoints import CheckpointManager
from adk_loop_lab.loop.policies import BudgetManager, StoppingPolicy
from adk_loop_lab.models import (
    BudgetConfig,
    Decision,
    EventType,
    LoopEvent,
    LoopRun,
    LoopState,
    Phase,
    RunStatus,
)
from adk_loop_lab.state.sqlite import SqliteStateStore
from adk_loop_lab.state.transactions import TransactionManager


@pytest.fixture
async def store() -> SqliteStateStore:
    s = SqliteStateStore(":memory:")
    await s.initialize()
    return s


@pytest.fixture
async def run_in_store(store: SqliteStateStore) -> LoopRun:
    run = LoopRun(example_id="test", goal="test")
    await store.save_run(run)
    return run


# ── TransactionManager ────────────────────────────────────────────────


class TestTransactionManager:
    async def test_commit_iteration_saves_run_and_state(
        self, store: SqliteStateStore, run_in_store: LoopRun
    ) -> None:
        txn = TransactionManager(store, run_in_store.run_id)
        state = LoopState(phase=Phase.VERIFY, progress_score=0.8)

        run_in_store.current_iteration = 2
        await txn.commit_iteration(run_in_store, state, [])

        loaded = await store.get_run(run_in_store.run_id)
        assert loaded is not None
        assert loaded.current_iteration == 2

        loaded_state = await store.get_state(run_in_store.run_id)
        assert loaded_state is not None
        assert loaded_state.phase == Phase.VERIFY

    async def test_commit_iteration_records_events(
        self, store: SqliteStateStore, run_in_store: LoopRun, tmp_path
    ) -> None:
        txn = TransactionManager(store, run_in_store.run_id)
        recorder = EventRecorder(base_dir=str(tmp_path))
        state = LoopState()

        event = LoopEvent(run_id=run_in_store.run_id, iteration=1, event_type=EventType.PHASE_ENTER)
        await txn.commit_iteration(run_in_store, state, [event], recorder)

        events = recorder.get_events(run_in_store.run_id)
        assert len(events) == 1


# ── BudgetManager ──────────────────────────────────────────────────────


class TestBudgetManager:
    def test_initial_state(self) -> None:
        config = BudgetConfig(max_iterations=10, max_model_calls=30, max_tool_calls=50)
        bm = BudgetManager(config)
        assert bm.state.iteration == 0
        assert bm.state.model_calls == 0
        assert bm.can_continue()

    def test_model_call_counting(self) -> None:
        config = BudgetConfig(max_model_calls=2)
        bm = BudgetManager(config)
        assert bm.can_continue()
        bm.record_model_call()
        bm.record_model_call()
        assert not bm.can_continue()

    def test_tool_call_counting(self) -> None:
        config = BudgetConfig(max_tool_calls=1)
        bm = BudgetManager(config)
        bm.record_tool_call()
        assert not bm.can_continue()

    def test_iteration_limit(self) -> None:
        config = BudgetConfig(max_iterations=3)
        bm = BudgetManager(config)
        for _ in range(3):
            bm.state.iteration += 1
        assert not bm.can_continue()

    def test_unlimited_duration(self) -> None:
        config = BudgetConfig(max_duration_seconds=None)
        bm = BudgetManager(config)
        assert bm.can_continue()  # No duration limit


# ── StoppingPolicy ─────────────────────────────────────────────────────


class TestStoppingPolicy:
    def setup_method(self) -> None:
        self.config = BudgetConfig(max_iterations=5, stagnation_threshold=3, max_model_calls=10)
        self.policy = StoppingPolicy(self.config)

    def test_success_when_all_criteria_met(self) -> None:
        bm = BudgetManager(self.config)
        assert self.policy.evaluate(bm, True, 0) == Decision.SUCCESS

    def test_continue_when_not_done(self) -> None:
        bm = BudgetManager(self.config)
        assert self.policy.evaluate(bm, False, 0) == Decision.CONTINUE

    def test_failed_on_fatal_error(self) -> None:
        bm = BudgetManager(self.config)
        assert self.policy.evaluate(bm, False, 0, fatal_error=True) == Decision.FAILED

    def test_budget_exhausted_on_model_calls(self) -> None:
        config = BudgetConfig(max_model_calls=1)
        bm = BudgetManager(config)
        bm.record_model_call()
        assert StoppingPolicy(config).evaluate(bm, False, 0) == Decision.BUDGET_EXHAUSTED

    def test_stagnated(self) -> None:
        bm = BudgetManager(self.config)
        assert self.policy.evaluate(bm, False, 3) == Decision.STAGNATED

    def test_success_overrides_budget(self) -> None:
        """Success should take priority over budget exhaustion."""
        config = BudgetConfig(max_model_calls=1)
        bm = BudgetManager(config)
        bm.record_model_call()
        bm.record_model_call()  # Now at 2, exceeds max of 1
        assert StoppingPolicy(config).evaluate(bm, True, 0) == Decision.SUCCESS

    def test_fatal_overrides_success(self) -> None:
        bm = BudgetManager(self.config)
        assert self.policy.evaluate(bm, True, 0, fatal_error=True) == Decision.FAILED


# ── CheckpointManager ──────────────────────────────────────────────────


class TestCheckpointManager:
    async def test_create_and_restore_checkpoint(
        self, store: SqliteStateStore, run_in_store: LoopRun
    ) -> None:
        recorder = EventRecorder()
        cpm = CheckpointManager(store, recorder)

        state = LoopState(phase=Phase.COMMIT, progress_score=0.75)
        ckpt_id = await cpm.create_checkpoint(run_in_store, state)
        assert ckpt_id is not None

        restored = await cpm.get_latest_checkpoint(run_in_store.run_id)
        assert restored is not None
        _restored_run, restored_state = restored
        assert restored_state.phase == Phase.COMMIT
        assert restored_state.progress_score == 0.75

    async def test_resume_run(
        self, store: SqliteStateStore, run_in_store: LoopRun
    ) -> None:
        recorder = EventRecorder()
        cpm = CheckpointManager(store, recorder)

        state = LoopState(phase=Phase.EXECUTE)
        await cpm.create_checkpoint(run_in_store, state)

        # Simulate interrupted state
        run_in_store.status = RunStatus.INTERRUPTED
        await store.save_run(run_in_store)

        result = await cpm.resume_run(run_in_store.run_id)
        assert result is not None
        resumed_run, _resumed_state = result
        assert resumed_run.status == RunStatus.RUNNING

    async def test_nonexistent_checkpoint(
        self, store: SqliteStateStore
    ) -> None:
        recorder = EventRecorder()
        cpm = CheckpointManager(store, recorder)
        assert await cpm.get_latest_checkpoint("nonexistent") is None
        assert await cpm.resume_run("nonexistent") is None
