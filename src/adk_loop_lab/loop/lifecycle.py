"""Loop lifecycle state machine.

Defines the allowed phase transitions and provides transition validation.
"""

from adk_loop_lab.models import Decision, Phase

PHASE_ORDER: list[Phase] = [
    Phase.DISCOVER,
    Phase.PLAN,
    Phase.EXECUTE,
    Phase.VERIFY,
    Phase.COMMIT,
    Phase.REFLECT,
    Phase.DECIDE,
]

TERMINAL_DECISIONS: set[Decision] = {
    Decision.SUCCESS,
    Decision.FAILED,
    Decision.BLOCKED,
    Decision.ESCALATE,
    Decision.BUDGET_EXHAUSTED,
    Decision.STAGNATED,
}


def next_phase(current: Phase) -> Phase:
    """Return the next phase in the lifecycle."""
    if current is Phase.DECIDE:
        return Phase.DISCOVER
    return PHASE_ORDER[phase_index(current) + 1]


def is_terminal(decision: Decision) -> bool:
    """Check if a decision stops the loop."""
    return decision in TERMINAL_DECISIONS


def phase_index(phase: Phase) -> int:
    """Return the numeric index of a phase (0-6)."""
    return PHASE_ORDER.index(phase)
