"""Core domain models for adk-loop-lab.

All models use Pydantic v2 for validation and serialization.
These are the authoritative data contracts — no ADK dependencies.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def _new_id() -> str:
    """Generate a sortable unique ID."""
    return uuid.uuid4().hex[:12]


def _utcnow() -> datetime:
    """Current UTC timestamp."""
    return datetime.now(tz=UTC)


# ── Lifecycle Phases ──────────────────────────────────────────────────


class Phase(StrEnum):
    """Loop lifecycle phases."""

    DISCOVER = "DISCOVER"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"
    VERIFY = "VERIFY"
    COMMIT = "COMMIT"
    REFLECT = "REFLECT"
    DECIDE = "DECIDE"


class Decision(StrEnum):
    """Terminal or continuation decisions."""

    CONTINUE = "CONTINUE"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    ESCALATE = "ESCALATE"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    STAGNATED = "STAGNATED"


class RunStatus(StrEnum):
    """Overall run status."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"


# ── Budget Models ─────────────────────────────────────────────────────


class BudgetConfig(BaseModel):
    """Budget constraints for a run."""

    max_iterations: int = Field(default=10, ge=1)
    max_model_calls: int = Field(default=30, ge=1)
    max_tool_calls: int = Field(default=50, ge=1)
    max_duration_seconds: int | None = Field(default=None, ge=1)
    stagnation_threshold: int = Field(
        default=3, ge=1, description="Consecutive iterations without progress before STAGNATED"
    )
    retry_max_attempts: int = Field(default=3, ge=0)
    retry_backoff_seconds: float = Field(default=2.0, ge=0)


class BudgetState(BaseModel):
    """Current budget consumption."""

    iteration: int = 0
    model_calls: int = 0
    tool_calls: int = 0
    started_at: datetime = Field(default_factory=_utcnow)
    last_activity_at: datetime = Field(default_factory=_utcnow)

    @property
    def elapsed_seconds(self) -> float:
        return (datetime.now(tz=UTC) - self.started_at).total_seconds()


# ── Run Models ────────────────────────────────────────────────────────


class AcceptanceCriterion(BaseModel):
    """A single acceptance criterion for the run."""

    key: str
    description: str
    met: bool = False


class LoopRun(BaseModel):
    """Top-level run metadata."""

    run_id: str = Field(default_factory=_new_id)
    example_id: str
    goal: str
    status: RunStatus = RunStatus.PENDING
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    current_iteration: int = 0
    max_iterations: int = 10
    budgets: BudgetConfig = Field(default_factory=BudgetConfig)
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)
    active_plan: str | None = None
    last_checkpoint_id: str | None = None
    last_decision: Decision | None = None


# ── State Models ──────────────────────────────────────────────────────


class LoopState(BaseModel):
    """Mutable state tracked within a run."""

    phase: Phase = Phase.DISCOVER
    facts: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    completed_actions: list[str] = Field(default_factory=list)
    pending_actions: list[str] = Field(default_factory=list)
    failed_attempts: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    artifact_refs: list[str] = Field(default_factory=list)
    evaluation_history: list[str] = Field(default_factory=list, description="Evaluation result IDs")
    progress_score: float = 0.0
    stagnation_count: int = 0


# ── Action Models ─────────────────────────────────────────────────────


class ActionType(StrEnum):
    """Classification of action types."""

    PLAN = "PLAN"
    TOOL_CALL = "TOOL_CALL"
    AGENT_CALL = "AGENT_CALL"
    ROUTE = "ROUTE"
    WAIT = "WAIT"
    NOOP = "NOOP"


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ActionProposal(BaseModel):
    """Model-generated bounded action proposal."""

    action_id: str = Field(default_factory=_new_id)
    action_type: ActionType
    description: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: dict[str, Any] = Field(default_factory=dict)
    expected_state_change: str = ""
    verification_plan: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    estimated_model_calls: int = 0
    estimated_tool_calls: int = 0
    idempotency_key: str | None = None
    rationale: str = ""
