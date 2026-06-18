# Failure Modes

Agentic loops fail in predictable ways. `adk-loop-lab` tries to make those
failures explicit, bounded, and recoverable where possible.

## Model API Errors

Recovery classification is defined in
[src/adk_loop_lab/loop/recovery.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/recovery.py).
The relevant failure types include:

- `MODEL_TIMEOUT`
- `MALFORMED_OUTPUT`
- `STATE_STORE_FAILURE`
- `TOOL_FAILURE`
- `EVALUATOR_ERROR`

`RecoveryPolicy.should_retry()` retries only selected transient failures:

- `MODEL_TIMEOUT`
- `MALFORMED_OUTPUT`
- `STATE_STORE_FAILURE`

It does not retry deterministic failures such as `TOOL_FAILURE` or
`EVALUATOR_ERROR`.

The retry loop is implemented by `RecoveryPolicy.with_recovery()`, which uses
bounded attempts and exponential backoff.

Real tests:

- transient planner failure recovers in
  [tests/unit/test_failure_injection.py](/home/rmax-10/src/adk-loop-lab/tests/unit/test_failure_injection.py)
- permanent planner failure terminates the run in the same file

## Tool Failures

Sandboxed tool behavior lives in:

- [src/adk_loop_lab/tools/shell.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/tools/shell.py)
- [src/adk_loop_lab/tools/filesystem.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/tools/filesystem.py)
- [src/adk_loop_lab/tools/safety.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/tools/safety.py)

Failure cases include:

- timeout: `SandboxShell.run()` raises `TimeoutError`
- disallowed command: command not in `ALLOWED_COMMANDS`
- sandbox escape attempt: path traversal or absolute path outside the sandbox

These behaviors are exercised in
[tests/unit/test_tools.py](/home/rmax-10/src/adk-loop-lab/tests/unit/test_tools.py)
and in the timeout failure injection test in
[tests/unit/test_failure_injection.py](/home/rmax-10/src/adk-loop-lab/tests/unit/test_failure_injection.py).

## State Corruption

The SQLite state store deliberately treats invalid persisted JSON as corruption,
not as trusted data.

- `SqliteStateStore.get_run()` returns `None` on validation failure
- `SqliteStateStore.get_state()` returns `None` on validation failure
- `CheckpointManager.get_latest_checkpoint()` skips corrupt checkpoint rows and
  falls back to older valid checkpoints

Relevant code:

- `src/adk_loop_lab/state/sqlite.py`
- `src/adk_loop_lab/loop/checkpoints.py`

Relevant tests:

- corrupt state row degrades gracefully in
  [tests/unit/test_failure_injection.py](/home/rmax-10/src/adk-loop-lab/tests/unit/test_failure_injection.py)
- corrupt latest checkpoint falls back to previous valid checkpoint in the same
  file

## Budget Exhaustion

Budgets are enforced by `BudgetManager` and `StoppingPolicy` in
[src/adk_loop_lab/loop/policies.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/policies.py).

Supported limits:

- iteration count
- model calls
- tool calls
- wall-clock duration

Budget exhaustion becomes the terminal decision `BUDGET_EXHAUSTED`. It is not a
model suggestion; it is a deterministic controller outcome.

Tests cover:

- max iterations
- max model calls
- max tool calls

See
[tests/unit/test_failure_injection.py](/home/rmax-10/src/adk-loop-lab/tests/unit/test_failure_injection.py).

## Stagnation

Stagnation is tracked in `LoopState.stagnation_count` and updated in
`LoopController._verify()`.

- if `progress_score` improves, stagnation resets to `0`
- otherwise it increments
- once the configured threshold is met, `StoppingPolicy` returns `STAGNATED`

This behavior is tested in
[tests/unit/test_failure_injection.py](/home/rmax-10/src/adk-loop-lab/tests/unit/test_failure_injection.py)
and
[tests/unit/test_loop.py](/home/rmax-10/src/adk-loop-lab/tests/unit/test_loop.py).

## Hallucinated Structured Output

Structured output errors are constrained in two places:

- Pydantic models validate persisted state, memory, and evaluations
- `LoopController._normalize_evaluation_result()` only accepts
  `EvaluationResult` instances or dict payloads that validate into one

For memory and state:

- `LoopRun.model_validate_json(...)`
- `LoopState.model_validate_json(...)`
- `MemoryRecord.model_validate_json(...)`

For evaluator results:

- `EvaluationResult.model_validate(...)`

This means malformed or hallucinated structure becomes a recoverable or fatal
runtime error instead of silently poisoning the loop.

## Recovery Summary

- transient model or persistence failures: bounded retry with backoff
- deterministic tool or evaluator failures: surface immediately
- corrupt persisted rows: return `None` or skip corrupt checkpoint rows
- repeated lack of progress: terminate with `STAGNATED`
- exhausted limits: terminate with `BUDGET_EXHAUSTED`
