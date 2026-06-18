"""Memory promotion logic.

Implements the lifecycle: CANDIDATE → VERIFIED → STALE → INVALIDATED.
Promotion requires evidence. Automatic staleness detection.
"""

from datetime import UTC, datetime, timedelta

from adk_loop_lab.memory.base import MemoryStore
from adk_loop_lab.models.memory import (
    MemoryKind,
    MemoryRecord,
    MemoryScope,
    MemoryStatus,
)


class MemoryPromoter:
    """Manages the memory promotion lifecycle."""

    def __init__(self, store: MemoryStore, min_confidence: float = 0.5) -> None:
        self._store = store
        self._min_confidence = min_confidence

    async def try_promote(
        self,
        record: MemoryRecord,
        evidence_refs: list[str],
    ) -> bool:
        """Attempt to promote a CANDIDATE to VERIFIED.

        Requirements:
        - Record must be CANDIDATE
        - Must have at least one evidence reference
        - Confidence must be >= min_confidence

        Returns True if promoted.
        """
        if record.status is not MemoryStatus.CANDIDATE:
            return False
        if not evidence_refs:
            return False
        if record.confidence < self._min_confidence:
            return False
        return await self._store.promote(record.memory_id, evidence_refs)

    async def add_candidate(
        self,
        kind: MemoryKind,
        content: str,
        source_run_id: str,
        source_iteration: int,
        confidence: float = 0.0,
        scope: MemoryScope | None = None,
    ) -> MemoryRecord:
        """Create and store a CANDIDATE memory record."""
        record = MemoryRecord(
            kind=kind,
            content=content,
            scope=scope or MemoryScope.RUN,
            source_run_id=source_run_id,
            source_iteration=source_iteration,
            status=MemoryStatus.CANDIDATE,
            confidence=confidence,
        )
        await self._store.add(record)
        return record

    async def mark_stale(
        self,
        memory_id: str,
        age_days: int = 30,
    ) -> bool:
        """Mark a VERIFIED record as STALE if older than age_days."""
        record = await self._store.get(memory_id)
        if record is None or record.status is not MemoryStatus.VERIFIED:
            return False

        if record.valid_from + timedelta(days=age_days) >= datetime.now(tz=UTC):
            return False

        stale_record = record.model_copy(
            update={
                "status": MemoryStatus.STALE,
                "valid_until": datetime.now(tz=UTC),
            }
        )
        await self._store.add(stale_record)
        return True

    async def invalidate_superseded(
        self,
        new_record: MemoryRecord,
    ) -> int:
        """Invalidate records superseded by a new record.

        Returns count of invalidated records.
        """
        superseded_records = await self._store.search(
            query="",
            scope=new_record.scope,
            kind=new_record.kind.value,
            limit=1000,
        )
        invalidated_count = 0

        for record in superseded_records:
            if record.supersedes != new_record.memory_id:
                continue

            metadata = dict(record.metadata)
            metadata["invalidated_reason"] = "superseded"
            updated_record = record.model_copy(
                update={
                    "status": MemoryStatus.INVALIDATED,
                    "invalidated_by": new_record.memory_id,
                    "valid_until": datetime.now(tz=UTC),
                    "metadata": metadata,
                }
            )
            await self._store.add(updated_record)
            invalidated_count += 1

        return invalidated_count
