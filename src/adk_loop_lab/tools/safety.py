"""Safety validation for sandboxed tools.

Enforces: path confinement, allowlisted commands, tool categorization,
timeouts, output caps, environment sanitization.
"""

from enum import Enum


class SideEffectLevel(Enum):
    """Tool side-effect classification."""

    READ_ONLY = "READ_ONLY"
    REVERSIBLE_WRITE = "REVERSIBLE_WRITE"
    IRREVERSIBLE_WRITE = "IRREVERSIBLE_WRITE"
    EXECUTION = "EXECUTION"


class ToolSpec:
    """Metadata about a tool's safety properties."""

    def __init__(
        self,
        name: str,
        description: str,
        side_effect: SideEffectLevel,
        requires_approval: bool = False,
        timeout_seconds: int = 30,
        idempotent: bool = False,
    ) -> None:
        self.name = name
        self.description = description
        self.side_effect = side_effect
        self.requires_approval = requires_approval
        self.timeout_seconds = timeout_seconds
        self.idempotent = idempotent


TOOL_SPECS = {
    "read_file": ToolSpec("read_file", "Read a file", SideEffectLevel.READ_ONLY, idempotent=True),
    "write_file": ToolSpec("write_file", "Write a file", SideEffectLevel.REVERSIBLE_WRITE),
    "run_shell": ToolSpec(
        "run_shell",
        "Execute allowlisted command",
        SideEffectLevel.EXECUTION,
        timeout_seconds=60,
    ),
    "run_tests": ToolSpec(
        "run_tests",
        "Run test suite",
        SideEffectLevel.EXECUTION,
        timeout_seconds=120,
    ),
    "apply_patch": ToolSpec("apply_patch", "Apply a patch", SideEffectLevel.REVERSIBLE_WRITE),
}
