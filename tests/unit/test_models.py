"""Tests for domain models — verify Pydantic schemas and defaults."""

import pytest
from pydantic import ValidationError

from adk_loop_lab.models import (
    AcceptanceCriterion,
    ActionProposal,
    ActionType,
    BudgetConfig,
    BudgetState,
    Decision,
    EventType,
    EvaluationResult,
    EvaluatorStatus,
    LoopEvent,
    LoopRun,
    LoopState,
    MemoryKind,
    MemoryRecord,
    Phase,
    RiskLevel,
    RunStatus,
)


class TestLoopRun:
    def test_defaults(self) -> None:
        run = LoopRun(example_id="level-1", goal="test goal")
        assert run.example_id == "level-1"
        assert run.goal == "test goal"
        assert run.status == RunStatus.PENDING
        assert run.current_iteration == 0
        assert len(run.run_id) == 12

    def test_custom_budgets(self) -> None:
        budgets = BudgetConfig(max_iterations=5, max_model_calls=10)
        run = LoopRun(example_id="x", goal="y", budgets=budgets)
        assert run.budgets.max_iterations == 5

    def test_acceptance_criteria(self) -> None:
        ac = AcceptanceCriterion(key="word_count", description="Must be 180-260 words")
        assert ac.met is False
        run = LoopRun(
            example_id="x", goal="y", acceptance_criteria=[ac]
        )
        assert len(run.acceptance_criteria) == 1


class TestLoopState:
    def test_default_phase(self) -> None:
        state = LoopState()
        assert state.phase == Phase.DISCOVER
        assert state.progress_score == 0.0
        assert state.stagnation_count == 0

    def test_facts_accumulate(self) -> None:
        state = LoopState(facts={"repo": "adk-loop-lab"})
        assert state.facts["repo"] == "adk-loop-lab"


class TestActionProposal:
    def test_minimal(self) -> None:
        prop = ActionProposal(action_type=ActionType.TOOL_CALL, description="Run tests")
        assert prop.action_type == ActionType.TOOL_CALL
        assert len(prop.action_id) == 12

    def test_risk_levels(self) -> None:
        prop = ActionProposal(
            action_type=ActionType.TOOL_CALL,
            description="rm -rf /",
            risk_level=RiskLevel.CRITICAL,
        )
        assert prop.risk_level == RiskLevel.CRITICAL


class TestEvaluationResult:
    def test_pass(self) -> None:
        result = EvaluationResult(evaluator_name="test_runner", status=EvaluatorStatus.PASS, score=1.0)
        assert result.status == EvaluatorStatus.PASS
        assert result.score == 1.0

    def test_fail_with_evidence(self) -> None:
        result = EvaluationResult(
            evaluator_name="lint",
            status=EvaluatorStatus.FAIL,
            score=0.0,
            failures=["E501 line too long"],
            evidence_refs=["event:abc123"],
        )
        assert len(result.failures) == 1
        assert len(result.evidence_refs) == 1


class TestLoopEvent:
    def test_serialization(self) -> None:
        event = LoopEvent(run_id="r1", iteration=1, event_type=EventType.RUN_STARTED)
        jsonl = event.to_jsonl()
        assert "r1" in jsonl
        assert "RUN_STARTED" in jsonl


class TestMemoryRecord:
    def test_candidate_default(self) -> None:
        mem = MemoryRecord(
            kind=MemoryKind.LESSON,
            content="Always verify before promoting",
            source_run_id="r1",
            source_iteration=0,
        )
        assert mem.status.value == "CANDIDATE"
        assert mem.confidence == 0.0

    def test_supersedes(self) -> None:
        newer = MemoryRecord(
            kind=MemoryKind.LESSON,
            content="Better rule",
            source_run_id="r2",
            source_iteration=3,
            supersedes="mem-abc",
        )
        assert newer.supersedes == "mem-abc"


class TestBudgetState:
    def test_tracking(self) -> None:
        budget = BudgetState(iteration=3, model_calls=5, tool_calls=10)
        assert budget.iteration == 3
        assert budget.model_calls == 5

    def test_elapsed_is_positive(self) -> None:
        budget = BudgetState()
        assert budget.elapsed_seconds >= 0


class TestBudgetConfig:
    def test_defaults(self) -> None:
        config = BudgetConfig()
        assert config.max_iterations == 10

    def test_custom(self) -> None:
        config = BudgetConfig(max_iterations=3, max_model_calls=5, stagnation_threshold=2)
        assert config.max_iterations == 3
        assert config.stagnation_threshold == 2


class TestEnums:
    def test_decision_values(self) -> None:
        assert Decision.CONTINUE.value == "CONTINUE"
        assert Decision.SUCCESS.value == "SUCCESS"
        assert len(list(Decision)) == 7

    def test_phase_order(self) -> None:
        phases = list(Phase)
        assert phases[0] == Phase.DISCOVER
        assert phases[-1] == Phase.DECIDE
