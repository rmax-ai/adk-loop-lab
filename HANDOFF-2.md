# HANDOFF-2

## What was built

- `src/adk_loop_lab/state/transactions.py`
  - Added `TransactionManager` for atomic per-iteration persistence using the existing shared SQLite connection.
  - Commits `LoopRun` and `LoopState` together inside one SQLite transaction.
  - Records JSONL events only after the SQLite commit succeeds, with recorder failures treated as best-effort.

- `src/adk_loop_lab/loop/checkpoints.py`
  - Added `CheckpointManager` with lazy creation of a `checkpoints` table in the same SQLite database.
  - Stores full serialized `LoopRun` and `LoopState` snapshots keyed by `{run_id}:{iteration}`.
  - Supports latest-checkpoint lookup and resume, including restoring `RUNNING` status and writing a `RUN_RESUMED` event.

- `src/adk_loop_lab/loop/policies.py`
  - Added mutable `BudgetManager` state for model/tool budget tracking.
  - Added deterministic `StoppingPolicy` evaluation for fatal error, success, budget exhaustion, stagnation, and duration exhaustion.

## Decisions made

- Transactional writes bypass `SqliteStateStore.save_run()` and `save_state()`.
  - Those Batch 1 helpers commit immediately, so atomic multi-write behavior required direct SQL on the shared connection.

- Checkpoints are persisted in SQLite, not in `var/runs/<run-id>/checkpoints/`.
  - This matches the Batch 2 request to keep checkpoint metadata in the state store while still emitting checkpoint/resume events to JSONL.

- Budget duration enforcement lives in `StoppingPolicy`, not `BudgetManager.can_continue()`.
  - This preserves the requested evaluation order where stagnation is checked before duration exhaustion.

## What Story 4.2 should know

- `TransactionManager` and `CheckpointManager` both rely on `SqliteStateStore._require_connection()`.
  - If the store API grows a first-class transaction surface later, these modules should switch to it.

- `BudgetManager` does not currently expose a `record_iteration()` helper.
  - Callers must update `budget.state.iteration` themselves until the loop controller owns that increment explicitly.

- Resume currently restores the latest checkpoint into both `runs` and `loop_states`.
  - Future loop orchestration can treat `resume_run()` as the authoritative state restore step.

- Recorder writes are intentionally best-effort after database commits.
  - SQLite remains the source of truth; JSONL traces may lag if disk writes fail.
