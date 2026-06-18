"""Deterministic budget and stopping policies."""

from datetime import UTC, datetime

from adk_loop_lab.models import BudgetConfig, BudgetState, Decision


class BudgetManager:
    """Tracks and enforces budget constraints."""

    def __init__(self, config: BudgetConfig) -> None:
        self._config = config
        self._state = BudgetState()

    @property
    def state(self) -> BudgetState:
        """Current budget consumption."""
        return self._state

    def record_model_call(self) -> None:
        """Increment model call counter."""
        self._state.model_calls += 1
        self._touch()

    def record_tool_call(self) -> None:
        """Increment tool call counter."""
        self._state.tool_calls += 1
        self._touch()

    def can_continue(self) -> bool:
        """Check if model, tool, and iteration budgets remain."""
        return not (
            self._state.iteration >= self._config.max_iterations
            or self._state.model_calls >= self._config.max_model_calls
            or self._state.tool_calls >= self._config.max_tool_calls
        )

    def _touch(self) -> None:
        self._state.last_activity_at = datetime.now(tz=UTC)


class StoppingPolicy:
    """Deterministic stopping-rule engine."""

    def __init__(self, config: BudgetConfig) -> None:
        self._config = config

    def evaluate(
        self,
        budget: BudgetManager,
        all_criteria_met: bool,
        stagnation_count: int,
        fatal_error: bool = False,
    ) -> Decision:
        """Evaluate stopping conditions and return the appropriate decision."""
        if fatal_error:
            return Decision.FAILED
        if all_criteria_met:
            return Decision.SUCCESS
        if not budget.can_continue():
            return Decision.BUDGET_EXHAUSTED
        if stagnation_count >= self._config.stagnation_threshold:
            return Decision.STAGNATED
        if (
            self._config.max_duration_seconds is not None
            and budget.state.elapsed_seconds >= self._config.max_duration_seconds
        ):
            return Decision.BUDGET_EXHAUSTED
        return Decision.CONTINUE
