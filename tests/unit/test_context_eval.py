"""Tests for context builder and evaluators."""

from adk_loop_lab.context.builder import ContextBuilder
from adk_loop_lab.evaluation.composite import evaluate_composite
from adk_loop_lab.evaluation.deterministic import (
    exact_match_validator,
    not_contains_validator,
    range_validator,
    schema_validator,
)
from adk_loop_lab.models import (
    CompositePolicy,
    EvaluationResult,
    EvaluatorStatus,
    LoopRun,
    LoopState,
)


class TestContextBuilder:
    def test_plan_context_includes_goal(self) -> None:
        builder = ContextBuilder()
        run = LoopRun(example_id="x", goal="build a thing")
        state = LoopState()
        ctx = builder.build_plan_context(run, state)
        assert "build a thing" in ctx

    def test_plan_context_includes_budget(self) -> None:
        builder = ContextBuilder()
        run = LoopRun(example_id="x", goal="test", max_iterations=5)
        state = LoopState()
        ctx = builder.build_plan_context(run, state)
        assert "5" in ctx  # max_iterations appears somewhere

    def test_reflect_context(self) -> None:
        builder = ContextBuilder()
        run = LoopRun(example_id="x", goal="test")
        state = LoopState(completed_actions=["action-1"])
        ctx = builder.build_reflect_context(run, state)
        assert "action-1" in ctx


class TestDeterministicEvaluators:
    def test_range_validator_pass(self) -> None:
        r = range_validator(150, 100, 200, "word_count")
        assert r.status == EvaluatorStatus.PASS

    def test_range_validator_fail(self) -> None:
        r = range_validator(50, 100, 200, "word_count")
        assert r.status == EvaluatorStatus.FAIL

    def test_not_contains_validator(self) -> None:
        r = not_contains_validator("clean text", ["forbidden"], "check")
        assert r.status == EvaluatorStatus.PASS

        r2 = not_contains_validator("has forbidden word", ["forbidden"], "check")
        assert r2.status == EvaluatorStatus.FAIL

    def test_exact_match_validator(self) -> None:
        r = exact_match_validator("hello world", "world")
        assert r.status == EvaluatorStatus.PASS

        r2 = exact_match_validator("hello world", "missing")
        assert r2.status == EvaluatorStatus.FAIL

    def test_schema_validator(self) -> None:
        data = {"name": "test", "count": 5}
        schema = {"name": str, "count": int}
        r = schema_validator(data, schema)
        assert r.status == EvaluatorStatus.PASS

    def test_schema_validator_missing_key(self) -> None:
        data = {"name": "test"}
        schema = {"name": str, "count": int}
        r = schema_validator(data, schema)
        assert r.status == EvaluatorStatus.FAIL

    def test_all_deterministic(self) -> None:
        for fn in [range_validator(100, 0, 200), not_contains_validator("x", ["y"])]:
            assert fn.is_deterministic


class TestCompositeEvaluator:
    def test_deterministic_veto(self) -> None:
        fail = EvaluationResult(evaluator_name="e1", status=EvaluatorStatus.FAIL, is_deterministic=True)
        result = evaluate_composite([fail], CompositePolicy.DETERMINISTIC_VETO)
        assert result.overall_status == EvaluatorStatus.FAIL
        assert result.veto_triggered

    def test_non_deterministic_no_veto(self) -> None:
        fail_nd = EvaluationResult(evaluator_name="e1", status=EvaluatorStatus.FAIL, is_deterministic=False)
        result = evaluate_composite([fail_nd], CompositePolicy.DETERMINISTIC_VETO)
        assert result.overall_status == EvaluatorStatus.PASS

    def test_all_required(self) -> None:
        p1 = EvaluationResult(evaluator_name="a", status=EvaluatorStatus.PASS)
        p2 = EvaluationResult(evaluator_name="b", status=EvaluatorStatus.PASS)
        result = evaluate_composite([p1, p2], CompositePolicy.ALL_REQUIRED)
        assert result.overall_status == EvaluatorStatus.PASS

    def test_all_required_one_fails(self) -> None:
        p1 = EvaluationResult(evaluator_name="a", status=EvaluatorStatus.PASS)
        f1 = EvaluationResult(evaluator_name="b", status=EvaluatorStatus.FAIL)
        result = evaluate_composite([p1, f1], CompositePolicy.ALL_REQUIRED)
        assert result.overall_status == EvaluatorStatus.FAIL

    def test_weighted_score(self) -> None:
        p1 = EvaluationResult(evaluator_name="a", status=EvaluatorStatus.PASS, score=1.0)
        f1 = EvaluationResult(evaluator_name="b", status=EvaluatorStatus.FAIL, score=0.0)
        result = evaluate_composite([p1, f1], CompositePolicy.WEIGHTED_SCORE)
        # Average = 0.5, below default threshold of 0.7
        assert result.overall_status == EvaluatorStatus.FAIL

    def test_quorum(self) -> None:
        p1 = EvaluationResult(evaluator_name="a", status=EvaluatorStatus.PASS)
        p2 = EvaluationResult(evaluator_name="b", status=EvaluatorStatus.PASS)
        f1 = EvaluationResult(evaluator_name="c", status=EvaluatorStatus.FAIL)
        result = evaluate_composite([p1, p2, f1], CompositePolicy.QUORUM)
        assert result.overall_status == EvaluatorStatus.PASS
