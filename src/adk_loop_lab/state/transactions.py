"""Transactional helpers for atomic loop-state commits."""

from datetime import UTC, datetime

import structlog

from adk_loop_lab.events.recorder import EventRecorder
from adk_loop_lab.models import LoopEvent, LoopRun, LoopState, RunStatus
from adk_loop_lab.state.sqlite import SqliteStateStore

logger = structlog.get_logger(__name__)


class TransactionManager:
    """Manages atomic state transactions for a run."""

    def __init__(self, store: SqliteStateStore, run_id: str) -> None:
        self._store = store
        self._run_id = run_id

    async def commit_iteration(
        self,
        run: LoopRun,
        state: LoopState,
        events: list[LoopEvent],
        recorder: EventRecorder | None = None,
    ) -> None:
        """Atomically save run, state, and iteration events."""
        connection = self._store._require_connection()
        committed = False

        run.current_iteration = max(
            run.current_iteration,
            max((event.iteration for event in events), default=run.current_iteration),
        )
        run.updated_at = datetime.now(tz=UTC)
        if run.status not in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.INTERRUPTED}:
            run.status = RunStatus.RUNNING

        try:
            await connection.execute("BEGIN")
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
                (self._run_id, state.model_dump_json()),
            )
            await connection.commit()
            committed = True
        except Exception:
            await connection.rollback()
            logger.exception("failed_to_commit_iteration", run_id=self._run_id)
            raise
        finally:
            if committed and recorder is not None:
                for event in events:
                    try:
                        recorder.record(event)
                    except Exception:
                        logger.exception(
                            "failed_to_record_iteration_event",
                            run_id=event.run_id,
                            event_type=event.event_type.value,
                            event_id=event.event_id,
                        )
