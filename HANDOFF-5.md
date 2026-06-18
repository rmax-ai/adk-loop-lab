# HANDOFF-5

## What was built

- `src/adk_loop_lab/loop/lifecycle.py`
  - Added the authoritative phase order for the deterministic loop lifecycle.
  - Added helpers for `next_phase()`, `is_terminal()`, and `phase_index()`.

- `src/adk_loop_lab/loop/recovery.py`
  - Added `FailureType` classification for model, tool, evaluator, and persistence failures.
  - Added `RecoveryPolicy` with bounded retries and exponential backoff for transient failures only.

- `src/adk_loop_lab/loop/controller.py`
  - Added the deterministic `LoopController` that runs `DISCOVER -> PLAN -> EXECUTE -> VERIFY -> COMMIT -> REFLECT -> DECIDE`.
  - Added per-phase event emission, iteration event buffering through commit, checkpoint creation, console output, progress tracking, stagnation detection, and checkpoint-based resume.
  - Added offline behavior for `PLAN` and `REFLECT` when no `agent_func` is configured.

## Verification completed

- Ran `uv run ruff check src`.
- Ran `uv run mypy src`.
- Ran import/helper sanity checks for `lifecycle.py`, `recovery.py`, and `controller.py`.

## Verification blocked

- The requested offline smoke script could not complete in this sandbox because `await aiosqlite.connect(':memory:')` hangs before `SqliteStateStore.initialize()` returns.
- That behavior reproduces outside the controller in a minimal script, so it appears to be an environment/runtime issue rather than a Phase 5 controller issue.

## Decisions made

- The commit boundary is the recovery boundary.
  - Iteration events from `DISCOVER` through `COMMIT` are buffered and persisted together during commit.
  - `REFLECT`, `DECIDE`, stop-decision, and iteration-complete events are recorded after the checkpoint, so resume restarts from the last fully committed state.

- Progress is evaluator-driven.
  - `LoopState.progress_score` is the average of evaluator scores for the iteration.
  - `stagnation_count` resets only when the score strictly improves.

- Success is determined conservatively.
  - If evaluators run, `SUCCESS` requires all evaluator results to be `PASS`.
  - If there are no evaluators, success falls back to explicit `acceptance_criteria` only.

## What Story 5.2 should know

- `PLAN` currently stores free-text output in `run.active_plan`, `state.facts["last_plan"]`, and optionally `state.pending_actions`.
  - If Story 5.2 introduces structured plan parsing, it should convert that text into `ActionProposal`-backed execution instead of relying on raw strings.

- Tool execution is intentionally minimal right now.
  - The controller treats the first `pending_actions` entry as the tool name and pulls optional args from `state.facts["tool_args"]`.
  - A richer action router can replace that without changing lifecycle sequencing.

- Resume currently restarts the loop from the last checkpointed state by calling `run()` again.
  - That means post-commit phases from the interrupted iteration may be re-run, but only after a deterministic committed state restore.
