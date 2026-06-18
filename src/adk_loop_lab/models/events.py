"""Event models — append-only event system.

Every event has a unique ID, timestamp, actor, and payload.
Events are written to JSONL files for machine-readable traces.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from adk_loop_lab.models.state import _new_id


class EventType(StrEnum):
    """Event types covering the full lifecycle."""

    # Run lifecycle
    RUN_STARTED = "RUN_STARTED"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_FAILED = "RUN_FAILED"
    RUN_INTERRUPTED = "RUN_INTERRUPTED"
    RUN_RESUMED = "RUN_RESUMED"

    # Iteration lifecycle
    ITERATION_STARTED = "ITERATION_STARTED"
    ITERATION_COMPLETED = "ITERATION_COMPLETED"

    # Phase transitions
    PHASE_ENTER = "PHASE_ENTER"
    PHASE_EXIT = "PHASE_EXIT"

    # Actions
    MODEL_CALL = "MODEL_CALL"
    MODEL_RESPONSE = "MODEL_RESPONSE"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"

    # Verification
    EVALUATION_RESULT = "EVALUATION_RESULT"
    VERIFICATION_PASSED = "VERIFICATION_PASSED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"

    # State
    STATE_CHANGE = "STATE_CHANGE"
    CHECKPOINT_CREATED = "CHECKPOINT_CREATED"

    # Memory
    MEMORY_CANDIDATE = "MEMORY_CANDIDATE"
    MEMORY_PROMOTED = "MEMORY_PROMOTED"
    MEMORY_INVALIDATED = "MEMORY_INVALIDATED"

    # Budget
    BUDGET_UPDATE = "BUDGET_UPDATE"
    BUDGET_WARNING = "BUDGET_WARNING"

    # Decision
    STOP_DECISION = "STOP_DECISION"
    PROGRESS_STAGNATED = "PROGRESS_STAGNATED"

    # Errors
    ERROR = "ERROR"
    RECOVERY = "RECOVERY"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"


class LoopEvent(BaseModel):
    """A single event in the run trace."""

    event_id: str = Field(default_factory=lambda: _new_id())
    run_id: str
    iteration: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    event_type: EventType
    actor: str = "system"
    payload: dict[str, Any] = Field(default_factory=dict)
    parent_event_id: str | None = None
    correlation_id: str | None = None

    def to_jsonl(self) -> str:
        """Serialize as a single JSON line."""
        return self.model_dump_json()
