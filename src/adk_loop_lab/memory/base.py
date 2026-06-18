"""Abstract memory store interface.

Vendor-neutral interface for storing and retrieving verified lessons.
Concrete implementations: SqliteMemoryStore (default), InMemoryMemoryStore (tests).
"""

from abc import ABC, abstractmethod

from adk_loop_lab.models.memory import MemoryRecord, MemoryScope


class MemoryStore(ABC):
    """Abstract interface for memory storage and retrieval."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the store (create tables, indices, etc.)."""

    @abstractmethod
    async def add(self, record: MemoryRecord) -> str:
        """Add a memory record. Returns the memory_id."""

    @abstractmethod
    async def get(self, memory_id: str) -> MemoryRecord | None:
        """Retrieve a memory record by ID."""

    @abstractmethod
    async def search(
        self,
        query: str,
        scope: MemoryScope | None = None,
        kind: str | None = None,
        limit: int = 10,
    ) -> list[MemoryRecord]:
        """Search memory records by text query.

        Args:
            query: Text to search for.
            scope: Optional scope filter.
            kind: Optional kind filter.
            limit: Maximum results.

        Returns:
            Matching records, ordered by relevance or recency.
        """

    @abstractmethod
    async def promote(self, memory_id: str, evidence_refs: list[str]) -> bool:
        """Promote a CANDIDATE record to VERIFIED with evidence.

        Returns True if promotion succeeded, False if record not found or not CANDIDATE.
        """

    @abstractmethod
    async def invalidate(self, memory_id: str, reason: str) -> bool:
        """Invalidate a record.

        Returns True if invalidation succeeded.
        """

    @abstractmethod
    async def close(self) -> None:
        """Close the store connection."""
