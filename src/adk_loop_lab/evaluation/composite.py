"""Composite evaluator — combines multiple evaluator results."""

from adk_loop_lab.models import (
    CompositePolicy,
    CompositeResult,
    EvaluationResult,
    EvaluatorStatus,
)


def evaluate_composite(
    results: list[EvaluationResult],
    policy: CompositePolicy = CompositePolicy.DETERMINISTIC_VETO,
) -> CompositeResult:
    """Combine multiple evaluation results according to a policy."""
    if not results:
        return CompositeResult(
            policy=policy,
            overall_status=EvaluatorStatus.SKIPPED,
            overall_score=0.0,
            results=[],
        )

    average_score = sum(result.score for result in results) / len(results)

    if policy is CompositePolicy.DETERMINISTIC_VETO:
        veto_result = next(
            (
                result
                for result in results
                if result.is_deterministic and result.status is EvaluatorStatus.FAIL
            ),
            None,
        )
        if veto_result is not None:
            return CompositeResult(
                policy=policy,
                overall_status=EvaluatorStatus.FAIL,
                overall_score=0.0,
                results=results,
                veto_triggered=True,
                veto_by=veto_result.evaluator_name,
            )
        return CompositeResult(
            policy=policy,
            overall_status=EvaluatorStatus.PASS,
            overall_score=average_score,
            results=results,
        )

    if policy is CompositePolicy.ALL_REQUIRED:
        passed = all(result.status is EvaluatorStatus.PASS for result in results)
        return CompositeResult(
            policy=policy,
            overall_status=EvaluatorStatus.PASS if passed else EvaluatorStatus.FAIL,
            overall_score=average_score if passed else 0.0,
            results=results,
        )

    if policy is CompositePolicy.WEIGHTED_SCORE:
        passed = average_score >= 0.7
        return CompositeResult(
            policy=policy,
            overall_status=EvaluatorStatus.PASS if passed else EvaluatorStatus.FAIL,
            overall_score=average_score,
            results=results,
        )

    pass_count = sum(1 for result in results if result.status is EvaluatorStatus.PASS)
    passed = pass_count > len(results) / 2
    return CompositeResult(
        policy=policy,
        overall_status=EvaluatorStatus.PASS if passed else EvaluatorStatus.FAIL,
        overall_score=average_score if passed else 0.0,
        results=results,
    )
