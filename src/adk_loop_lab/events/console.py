"""Console display formatting for loop progress."""

from adk_loop_lab.models import (
    BudgetState,
    Decision,
    EvaluationResult,
    EvaluatorStatus,
    LoopRun,
    LoopState,
)


def format_iteration_header(run: LoopRun, state: LoopState, budget: BudgetState) -> str:
    """Format the iteration header display."""
    return "\n".join(
        [
            f"RUN: {run.run_id}",
            f"ITERATION {run.current_iteration}/{run.max_iterations}",
            f"PHASE: {state.phase.value}",
            f"BUDGET: model_calls={budget.model_calls} tool_calls={budget.tool_calls}",
            f"ELAPSED: {budget.elapsed_seconds:.1f}s",
        ]
    )


def format_evaluation_line(result: EvaluationResult) -> str:
    """Format a single evaluator result for display."""
    symbol = _status_symbol(result.status)
    detail = result.summary
    if not detail and result.failures:
        detail = "; ".join(result.failures)
    if detail:
        return f"{symbol} {result.evaluator_name}: {detail}"
    return f"{symbol} {result.evaluator_name}"


def format_decision(decision: Decision, reason: str = "") -> str:
    """Format the stop/continue decision."""
    if reason:
        return f"DECISION: {decision.value} - {reason}"
    return f"DECISION: {decision.value}"


def _status_symbol(status: EvaluatorStatus) -> str:
    if status is EvaluatorStatus.PASS:
        return "✓"
    return "✗"
