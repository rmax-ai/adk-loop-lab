"""Domain models for adk-loop-lab.

All models use Pydantic v2 for validation and serialization.
These contracts are the authoritative data shapes — no ADK dependencies.
"""

from adk_loop_lab.models.budgets import BudgetConfig, BudgetState
from adk_loop_lab.models.evaluations import (
    CompositePolicy,
    CompositeResult,
    EvaluationResult,
    EvaluatorStatus,
)
from adk_loop_lab.models.events import EventType, LoopEvent
from adk_loop_lab.models.memory import MemoryKind, MemoryRecord, MemoryScope, MemoryStatus
from adk_loop_lab.models.plans import ActionProposal, ActionType, RiskLevel
from adk_loop_lab.models.state import (
    AcceptanceCriterion,
    Decision,
    LoopRun,
    LoopState,
    Phase,
    RunStatus,
)

__all__ = [
    "AcceptanceCriterion",
    "ActionProposal",
    # Plans
    "ActionType",
    # Budgets
    "BudgetConfig",
    "BudgetState",
    "CompositePolicy",
    "CompositeResult",
    "Decision",
    "EvaluationResult",
    # Evaluation
    "EvaluatorStatus",
    # Events
    "EventType",
    "LoopEvent",
    "LoopRun",
    "LoopState",
    # Memory
    "MemoryKind",
    "MemoryRecord",
    "MemoryScope",
    "MemoryStatus",
    # State
    "Phase",
    "RiskLevel",
    "RunStatus",
]
