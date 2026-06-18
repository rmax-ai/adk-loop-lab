"""Recovery policies for loop execution failures."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class FailureType(Enum):
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"
    TOOL_FAILURE = "TOOL_FAILURE"
    STATE_STORE_FAILURE = "STATE_STORE_FAILURE"
    EVALUATOR_ERROR = "EVALUATOR_ERROR"


class RecoveryPolicy:
    """Deterministic recovery policy with bounded retries."""

    def __init__(self, max_attempts: int = 3, backoff_seconds: float = 2.0) -> None:
        self._max_attempts = max_attempts
        self._backoff_seconds = backoff_seconds

    async def with_recovery(
        self,
        operation: str,
        fn: Callable[..., Awaitable[T]],
        *args: Any,
        failure_type: FailureType | None = None,
    ) -> T:
        """Execute an operation with bounded retry on failure."""
        attempts = max(self._max_attempts, 1)

        for attempt in range(1, attempts + 1):
            try:
                return await fn(*args)
            except Exception as error:
                can_retry = (
                    failure_type is not None
                    and self.should_retry(failure_type)
                    and attempt < attempts
                )
                logger.warning(
                    "recovery_attempt_failed",
                    extra={
                        "operation": operation,
                        "attempt": attempt,
                        "max_attempts": attempts,
                        "failure_type": failure_type.value if failure_type else None,
                        "retrying": can_retry,
                        "error": str(error),
                    },
                )
                if not can_retry:
                    raise RuntimeError(f"{operation} failed after {attempt} attempt(s)") from error
                await asyncio.sleep(self._backoff_seconds * (2 ** (attempt - 1)))

        raise RuntimeError(f"{operation} failed without executing")

    def should_retry(self, failure_type: FailureType) -> bool:
        """Check if this failure type should be retried."""
        return failure_type in {
            FailureType.MODEL_TIMEOUT,
            FailureType.MALFORMED_OUTPUT,
            FailureType.STATE_STORE_FAILURE,
        }
