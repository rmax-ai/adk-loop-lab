# HANDOFF-1

## What was built

- `src/adk_loop_lab/state/sqlite.py`
  - Added `SqliteStateStore` with async initialization, run/state save and load, filtered run listing, and connection teardown.
  - Persists `LoopRun` and `LoopState` as JSON using Pydantic `model_dump_json()` and restores with `model_validate_json()`.
  - Stores run metadata in `runs` and mutable state in `loop_states`.

- `src/adk_loop_lab/events/recorder.py`
  - Added synchronous append-only JSONL event recording to `var/runs/<run_id>/events.jsonl`.
  - Added readback support returning validated `LoopEvent` objects.

- `src/adk_loop_lab/events/console.py`
  - Added minimal human-readable formatters for iteration headers, evaluator lines, and decisions.

## Decisions made

- `SqliteStateStore` keeps one shared async SQLite connection after `initialize()`.
  - This is required for correct `:memory:` behavior across multiple method calls in the same store instance.

- Save operations use SQLite upsert semantics via `ON CONFLICT ... DO UPDATE`.
  - This matches the requested insert-or-replace behavior while keeping the SQL explicit.

- Console formatting uses the public `adk_loop_lab.models` exports.
  - This keeps imports aligned with the package API and avoids coupling callers to internal submodules.

- Evaluation display maps only `PASS` to `✓`.
  - All other evaluator statuses currently render as `✗` to preserve the requested simple pass/fail shape.

## What Batch 2 should know

- `format_iteration_header()` currently uses `run.current_iteration`, not `budget.iteration`.
  - If the loop controller treats budget iteration as the authoritative counter, the formatter may need to switch.

- `format_evaluation_line()` prefers `summary`, then falls back to joined `failures`.
  - If richer console output is needed later, recommendations/evidence can be added without changing recorder or state store behavior.

- `loop_states` does not currently enforce that a matching run already exists before save.
  - SQLite foreign keys exist in schema, but if strict runtime enforcement is desired, enable `PRAGMA foreign_keys = ON` during initialization.

- No tests were added in this batch by design.
