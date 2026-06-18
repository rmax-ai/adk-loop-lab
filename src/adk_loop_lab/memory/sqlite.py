"""SQLite-backed memory store with FTS5 full-text search."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import structlog

from adk_loop_lab.memory.base import MemoryStore
from adk_loop_lab.models.memory import MemoryRecord, MemoryScope, MemoryStatus

logger = structlog.get_logger(__name__)


class _CursorAdapter:
    """Async-shaped wrapper around a ``sqlite3`` cursor."""

    def __init__(self, cursor: sqlite3.Cursor) -> None:
        self._cursor = cursor

    async def fetchone(self) -> tuple[Any, ...] | None:
        return self._cursor.fetchone()  # type: ignore[no-any-return]

    async def fetchall(self) -> list[tuple[Any, ...]]:
        return self._cursor.fetchall()

    async def close(self) -> None:
        self._cursor.close()


class _ConnectionAdapter:
    """Async-shaped wrapper around a ``sqlite3`` connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    async def execute(
        self,
        sql: str,
        parameters: tuple[Any, ...] | list[str | int] = (),
    ) -> _CursorAdapter:
        cursor = self._connection.execute(sql, parameters)
        return _CursorAdapter(cursor)

    async def commit(self) -> None:
        self._connection.commit()

    async def close(self) -> None:
        self._connection.close()


class SqliteMemoryStore(MemoryStore):
    """SQLite-backed memory store with FTS5 search."""

    def __init__(self, db_path: str = "var/memory/loop_lab_memory.db") -> None:
        self._db_path = db_path
        self._connection: _ConnectionAdapter | None = None

    async def initialize(self) -> None:
        """Create tables and FTS5 virtual table."""
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        raw_connection = sqlite3.connect(self._db_path)
        self._connection = _ConnectionAdapter(raw_connection)
        connection = self._require_connection()
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_records (
                memory_id TEXT PRIMARY KEY,
                scope TEXT NOT NULL,
                kind TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                data TEXT NOT NULL
            )
            """
        )
        await connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                memory_id UNINDEXED,
                content
            )
            """
        )
        await connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_records_scope ON memory_records (scope)"
        )
        await connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_records_kind ON memory_records (kind)"
        )
        await connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_records_status ON memory_records (status)"
        )
        await connection.commit()

    async def add(self, record: MemoryRecord) -> str:
        """Insert a memory record."""
        connection = self._require_connection()
        await connection.execute(
            """
            INSERT INTO memory_records (memory_id, scope, kind, status, created_at, data)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(memory_id) DO UPDATE SET
                scope = excluded.scope,
                kind = excluded.kind,
                status = excluded.status,
                created_at = excluded.created_at,
                data = excluded.data
            """,
            (
                record.memory_id,
                record.scope.value,
                record.kind.value,
                record.status.value,
                record.created_at.isoformat(),
                record.model_dump_json(),
            ),
        )
        await connection.execute("DELETE FROM memory_fts WHERE memory_id = ?", (record.memory_id,))
        await connection.execute(
            "INSERT INTO memory_fts (memory_id, content) VALUES (?, ?)",
            (record.memory_id, record.content),
        )
        await connection.commit()
        return record.memory_id

    async def get(self, memory_id: str) -> MemoryRecord | None:
        """Retrieve by ID."""
        connection = self._require_connection()
        cursor = await connection.execute(
            "SELECT data FROM memory_records WHERE memory_id = ?",
            (memory_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None
        return MemoryRecord.model_validate_json(row[0])

    async def search(
        self,
        query: str,
        scope: MemoryScope | None = None,
        kind: str | None = None,
        limit: int = 10,
    ) -> list[MemoryRecord]:
        """FTS5 search across memory records."""
        connection = self._require_connection()
        safe_limit = max(1, limit)
        filters: list[str] = []
        params: list[str | int] = []

        if scope is not None:
            filters.append("mr.scope = ?")
            params.append(scope.value)
        if kind is not None:
            filters.append("mr.kind = ?")
            params.append(kind)

        if query.strip():
            sql = """
                SELECT mr.data
                FROM memory_records AS mr
                JOIN memory_fts AS mf ON mr.memory_id = mf.memory_id
                WHERE mf.content MATCH ?
            """
            params = [query, *params]
        else:
            sql = """
                SELECT mr.data
                FROM memory_records AS mr
                WHERE 1 = 1
            """

        if filters:
            sql = f"{sql} AND {' AND '.join(filters)}"

        sql = f"{sql} ORDER BY mr.created_at DESC LIMIT ?"
        params.append(safe_limit)
        cursor = await connection.execute(sql, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return [MemoryRecord.model_validate_json(row[0]) for row in rows]

    async def promote(self, memory_id: str, evidence_refs: list[str]) -> bool:
        """Promote CANDIDATE to VERIFIED."""
        record = await self.get(memory_id)
        if record is None or record.status is not MemoryStatus.CANDIDATE:
            return False

        combined_evidence = list(dict.fromkeys([*record.evidence_refs, *evidence_refs]))
        promoted_record = record.model_copy(
            update={
                "status": MemoryStatus.VERIFIED,
                "evidence_refs": combined_evidence,
                "valid_from": datetime.now(tz=UTC),
            }
        )
        await self.add(promoted_record)
        return True

    async def invalidate(self, memory_id: str, reason: str) -> bool:
        """Set status to INVALIDATED."""
        record = await self.get(memory_id)
        if record is None:
            return False

        metadata = dict(record.metadata)
        metadata["invalidation_reason"] = reason
        invalidated_record = record.model_copy(
            update={
                "status": MemoryStatus.INVALIDATED,
                "valid_until": datetime.now(tz=UTC),
                "metadata": metadata,
            }
        )
        await self.add(invalidated_record)
        return True

    async def close(self) -> None:
        """Close the connection."""
        if self._connection is None:
            return

        try:
            await self._connection.close()
        except Exception:
            logger.exception("failed_to_close_memory_store", db_path=self._db_path)
            raise
        finally:
            self._connection = None

    def _require_connection(self) -> _ConnectionAdapter:
        if self._connection is None:
            raise RuntimeError("SqliteMemoryStore is not initialized")
        return self._connection
