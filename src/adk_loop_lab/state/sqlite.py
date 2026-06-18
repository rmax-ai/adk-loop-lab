"""SQLite-backed state persistence for loop runs."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import structlog

from adk_loop_lab.models import LoopRun, LoopState

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
        parameters: tuple[Any, ...] = (),
    ) -> _CursorAdapter:
        cursor = self._connection.execute(sql, parameters)
        return _CursorAdapter(cursor)

    async def commit(self) -> None:
        self._connection.commit()

    async def rollback(self) -> None:
        self._connection.rollback()

    async def close(self) -> None:
        self._connection.close()


class SqliteStateStore:
    """SQLite-backed state store for loop runs."""

    def __init__(self, db_path: str = "var/state/loop_lab.db") -> None:
        self._db_path = db_path
        self._connection: _ConnectionAdapter | None = None

    async def initialize(self) -> None:
        """Create tables if they don't exist."""
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        raw_connection = sqlite3.connect(self._db_path)
        self._connection = _ConnectionAdapter(raw_connection)
        connection = self._require_connection()
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                example_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                data TEXT NOT NULL
            )
            """
        )
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS loop_states (
                run_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs (run_id) ON DELETE CASCADE
            )
            """
        )
        await connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_runs_example_id ON runs (example_id)"
        )
        await connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_runs_status ON runs (status)"
        )
        await connection.commit()

    async def save_run(self, run: LoopRun) -> None:
        """Insert or replace a run record."""
        connection = self._require_connection()
        await connection.execute(
            """
            INSERT INTO runs (run_id, example_id, status, created_at, updated_at, data)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                example_id = excluded.example_id,
                status = excluded.status,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                data = excluded.data
            """,
            (
                run.run_id,
                run.example_id,
                run.status.value,
                run.created_at.isoformat(),
                run.updated_at.isoformat(),
                run.model_dump_json(),
            ),
        )
        await connection.commit()

    async def get_run(self, run_id: str) -> LoopRun | None:
        """Retrieve a run by ID."""
        connection = self._require_connection()
        cursor = await connection.execute("SELECT data FROM runs WHERE run_id = ?", (run_id,))
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None
        return LoopRun.model_validate_json(row[0])

    async def save_state(self, run_id: str, state: LoopState) -> None:
        """Save the current loop state for a run."""
        connection = self._require_connection()
        await connection.execute(
            """
            INSERT INTO loop_states (run_id, data)
            VALUES (?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                data = excluded.data
            """,
            (run_id, state.model_dump_json()),
        )
        await connection.commit()

    async def get_state(self, run_id: str) -> LoopState | None:
        """Retrieve the loop state for a run."""
        connection = self._require_connection()
        cursor = await connection.execute(
            "SELECT data FROM loop_states WHERE run_id = ?",
            (run_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row is None:
            return None
        return LoopState.model_validate_json(row[0])

    async def list_runs(self, example_id: str | None = None, limit: int = 20) -> list[LoopRun]:
        """List runs, optionally filtered by example ID."""
        connection = self._require_connection()
        if example_id is None:
            cursor = await connection.execute(
                """
                SELECT data
                FROM runs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
        else:
            cursor = await connection.execute(
                """
                SELECT data
                FROM runs
                WHERE example_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (example_id, limit),
            )
        rows = await cursor.fetchall()
        await cursor.close()
        return [LoopRun.model_validate_json(row[0]) for row in rows]

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection is None:
            return

        try:
            await self._connection.close()
        except Exception:
            logger.exception("failed_to_close_state_store", db_path=self._db_path)
            raise
        finally:
            self._connection = None

    def _require_connection(self) -> _ConnectionAdapter:
        if self._connection is None:
            raise RuntimeError("SqliteStateStore is not initialized")
        return self._connection
