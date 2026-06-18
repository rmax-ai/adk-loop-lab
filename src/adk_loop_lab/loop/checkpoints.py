"""Checkpoint persistence and resume helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from pydantic import ValidationError

from adk_loop_lab.events.recorder import EventRecorder
from adk_loop_lab.models import EventType, LoopEvent, LoopRun, LoopState, RunStatus
from adk_loop_lab.state.sqlite import SqliteStateStore

logger = structlog.get_logger(__name__)


class CheckpointManager:
    """Manages iteration checkpoints for run resume."""

    def __init__(self, store: SqliteStateStore, recorder: EventRecorder) -> None:
        self._store = store
        self._recorder = recorder

    async def create_checkpoint(self, run: LoopRun, state: LoopState) -> str:
        """Create a checkpoint after a completed iteration."""
        connection = self._store._require_connection()
        await self._ensure_table()

        checkpoint_id = f"{run.run_id}:{run.current_iteration}"
        run.last_checkpoint_id = checkpoint_id
        run.updated_at = datetime.now(tz=UTC)

        await connection.execute("BEGIN")
        try:
            await connection.execute(
                """
                INSERT INTO checkpoints (
                    checkpoint_id,
                    run_id,
                    iteration,
                    created_at,
                    run_data,
                    state_data
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(checkpoint_id) DO UPDATE SET
                    iteration = excluded.iteration,
                    created_at = excluded.created_at,
                    run_data = excluded.run_data,
                    state_data = excluded.state_data
                """,
                (
                    checkpoint_id,
                    run.run_id,
                    run.current_iteration,
                    run.updated_at.isoformat(),
                    run.model_dump_json(),
                    state.model_dump_json(),
                ),
            )
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
        except Exception:
            await connection.rollback()
            logger.exception("failed_to_create_checkpoint", run_id=run.run_id)
            raise

        try:
            self._recorder.record(
                LoopEvent(
                    run_id=run.run_id,
                    iteration=run.current_iteration,
                    event_type=EventType.CHECKPOINT_CREATED,
                    payload={"checkpoint_id": checkpoint_id},
                )
            )
        except Exception:
            logger.exception(
                "failed_to_record_checkpoint_event",
                run_id=run.run_id,
                checkpoint_id=checkpoint_id,
            )

        return checkpoint_id

    async def get_latest_checkpoint(self, run_id: str) -> tuple[LoopRun, LoopState] | None:
        """Retrieve the latest valid checkpoint state for a run."""
        connection = self._store._require_connection()
        await self._ensure_table()

        cursor = await connection.execute(
            """
            SELECT checkpoint_id, run_data, state_data
            FROM checkpoints
            WHERE run_id = ?
            ORDER BY iteration DESC, created_at DESC
            """,
            (run_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
        for row in rows:
            checkpoint_id, run_data, state_data = row
            try:
                return (
                    LoopRun.model_validate_json(run_data),
                    LoopState.model_validate_json(state_data),
                )
            except ValidationError:
                logger.warning(
                    "corrupt_checkpoint_row",
                    run_id=run_id,
                    checkpoint_id=checkpoint_id,
                )

        return None

    async def resume_run(self, run_id: str) -> tuple[LoopRun, LoopState] | None:
        """Resume a run from its latest checkpoint."""
        checkpoint = await self.get_latest_checkpoint(run_id)
        if checkpoint is None:
            return None

        run, state = checkpoint
        connection = self._store._require_connection()

        run.status = RunStatus.RUNNING
        run.updated_at = datetime.now(tz=UTC)

        await connection.execute("BEGIN")
        try:
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
            await connection.execute(
                """
                INSERT INTO loop_states (run_id, data)
                VALUES (?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    data = excluded.data
                """,
                (run.run_id, state.model_dump_json()),
            )
            await connection.commit()
        except Exception:
            await connection.rollback()
            logger.exception("failed_to_resume_run", run_id=run_id)
            raise

        try:
            self._recorder.record(
                LoopEvent(
                    run_id=run.run_id,
                    iteration=run.current_iteration,
                    event_type=EventType.RUN_RESUMED,
                    payload={"checkpoint_id": run.last_checkpoint_id},
                )
            )
        except Exception:
            logger.exception(
                "failed_to_record_resume_event",
                run_id=run.run_id,
                checkpoint_id=run.last_checkpoint_id,
            )

        return run, state

    async def _ensure_table(self) -> None:
        connection = self._store._require_connection()
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                iteration INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                run_data TEXT NOT NULL,
                state_data TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs (run_id) ON DELETE CASCADE
            )
            """
        )
        await connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_checkpoints_run_id_iteration
            ON checkpoints (run_id, iteration DESC)
            """
        )
        await connection.commit()
