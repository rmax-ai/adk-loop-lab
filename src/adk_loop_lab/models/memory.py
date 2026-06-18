"""Memory models — vendor-neutral memory record.

Memory records progress through: CANDIDATE → VERIFIED → STALE → INVALIDATED.
Promotion requires evidence. The interface is abstracted for pluggable backends.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from adk_loop_lab.models.state import _new_id


class MemoryStatus(StrEnum):
    """Lifecycle status of a memory record."""

    CANDIDATE = "CANDIDATE"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    STALE = "STALE"
    INVALIDATED = "INVALIDATED"


class MemoryKind(StrEnum):
    """Classification of memory records."""

    LESSON = "LESSON"
    FAILED_APPROACH = "FAILED_APPROACH"
    VERIFIED_PATTERN = "VERIFIED_PATTERN"
    OBSERVATION = "OBSERVATION"
    RISK_WARNING = "RISK_WARNING"


class MemoryScope(StrEnum):
    """Visibility scope of a memory record."""

    RUN = "RUN"
    EXAMPLE = "EXAMPLE"
    CROSS_RUN = "CROSS_RUN"


class MemoryRecord(BaseModel):
    """A durable memory record with evidence tracking."""

    memory_id: str = Field(default_factory=_new_id)
    kind: MemoryKind
    content: str
    scope: MemoryScope = MemoryScope.RUN
    source_run_id: str
    source_iteration: int
    status: MemoryStatus = MemoryStatus.CANDIDATE
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)
    valid_from: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    valid_until: datetime | None = None
    supersedes: str | None = None
    invalidated_by: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)
