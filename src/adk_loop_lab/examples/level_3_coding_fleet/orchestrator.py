"""Multi-agent orchestration for the coding fleet example."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from adk_loop_lab.tools.filesystem import SandboxFilesystem
from adk_loop_lab.tools.shell import SandboxShell


class AgentRoute(StrEnum):
    """Valid routing targets for the coding workflow."""

    INVESTIGATE = "investigate"
    IMPLEMENT = "implement"
    TEST_DESIGN = "test_design"
    CLARIFY = "clarify"
    ESCALATE = "escalate"


class FailureType(StrEnum):
    """Failure categories produced by sandbox verification."""

    TEST_FAILURE = "TEST_FAILURE"
    LINT_FAILURE = "LINT_FAILURE"
    TYPE_CHECK_FAILURE = "TYPE_CHECK_FAILURE"
    REQUIREMENT_GAP = "REQUIREMENT_GAP"


@dataclass
class FailureRecord:
    """Record of a failed approach to prevent repetition."""

    approach_hash: str
    error_signature: str
    iteration: int
    retry_count: int = 0
    blocked: bool = False


class CodingOrchestrator:
    """Orchestrate repository inspection, execution, and failure memory."""

    def __init__(self, sandbox_dir: str) -> None:
        self.fs = SandboxFilesystem(sandbox_dir)
        self.shell = SandboxShell(sandbox_dir)
        self.failure_history: list[FailureRecord] = []
        self.completed_actions: list[str] = []

    def route(self, plan: dict[str, Any]) -> AgentRoute:
        """Route a plan to a valid specialist target."""
        action = str(plan.get("action", "")).lower()
        if any(token in action for token in ("investigate", "inspect", "read")):
            return AgentRoute.INVESTIGATE
        if any(token in action for token in ("test", "verify")):
            return AgentRoute.TEST_DESIGN
        if any(token in action for token in ("implement", "add", "modify", "patch", "fix")):
            return AgentRoute.IMPLEMENT
        if any(token in action for token in ("clarify", "question")):
            return AgentRoute.CLARIFY
        if any(token in action for token in ("escalate", "blocked")):
            return AgentRoute.ESCALATE
        return AgentRoute.CLARIFY

    def plan_hash(self, plan: dict[str, Any]) -> str:
        """Hash the actionable shape of a plan."""
        payload = {
            "files": sorted(str(item) for item in plan.get("files", [])),
            "description": str(plan.get("description", "")),
        }
        raw = json.dumps(payload, sort_keys=True)
        return hashlib.md5(raw.encode("utf-8"), usedforsecurity=False).hexdigest()[:8]

    def check_failure_repetition(self, approach_hash: str) -> bool:
        """Return True when an approach is blocked due to repeated failure."""
        return any(
            record.approach_hash == approach_hash and record.blocked
            for record in self.failure_history
        )

    def record_failure(self, approach_hash: str, error: str, iteration: int) -> None:
        """Record a failed approach and block it after repeated retries."""
        error_signature = error.strip().splitlines()[0] if error.strip() else "unknown"
        for record in self.failure_history:
            if record.approach_hash != approach_hash:
                continue
            record.retry_count += 1
            record.error_signature = error_signature
            record.iteration = iteration
            if record.retry_count >= 3:
                record.blocked = True
            return

        self.failure_history.append(
            FailureRecord(
                approach_hash=approach_hash,
                error_signature=error_signature,
                iteration=iteration,
                retry_count=1,
                blocked=False,
            )
        )

    def get_patch(self) -> str | None:
        """Return the current git diff from the sandbox, if any."""
        exit_code, stdout, stderr = self.shell.run("git diff")
        if exit_code != 0:
            return stderr.strip() or stdout.strip() or None
        return stdout.strip() or None
