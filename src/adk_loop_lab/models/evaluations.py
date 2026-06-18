"""Evaluation models — verifier outputs and composite policies."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from adk_loop_lab.models.state import _new_id


class EvaluatorStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class CompositePolicy(StrEnum):
    """How to combine multiple evaluator results."""

    ALL_REQUIRED = "ALL_REQUIRED"
    WEIGHTED_SCORE = "WEIGHTED_SCORE"
    QUORUM = "QUORUM"
    DETERMINISTIC_VETO = "DETERMINISTIC_VETO"


class EvaluationResult(BaseModel):
    """Output from a single evaluator."""

    evaluation_id: str = Field(default_factory=_new_id)
    evaluator_name: str
    status: EvaluatorStatus
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    is_deterministic: bool = True
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class CompositeResult(BaseModel):
    """Aggregated result from multiple evaluators."""

    policy: CompositePolicy
    overall_status: EvaluatorStatus
    overall_score: float = Field(default=0.0, ge=0.0, le=1.0)
    results: list[EvaluationResult] = Field(default_factory=list)
    veto_triggered: bool = False
    veto_by: str | None = None
