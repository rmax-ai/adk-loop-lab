# HANDOFF-13

## Scope

Phase 10.1 added failure-injection coverage and golden trace coverage for the
loop controller and the three example flows.

## Files Added

- `tests/unit/test_failure_injection.py`
- `tests/golden/__init__.py`
- `tests/golden/test_golden_traces.py`
- `tests/golden/traces/__init__.py`
- `tests/golden/traces/level_1_trace.jsonl`
- `tests/golden/traces/level_2_trace.jsonl`
- `tests/golden/traces/level_3_trace.jsonl`

## Runtime Changes

- `src/adk_loop_lab/state/sqlite.py`
  - Corrupt `runs` and `loop_states` JSON rows now degrade gracefully instead of
    raising during read/list operations.
- `src/adk_loop_lab/loop/checkpoints.py`
  - Checkpoint restore now skips corrupt checkpoint rows and falls back to the
    latest valid checkpoint for the run.
- `src/adk_loop_lab/loop/controller.py`
  - `resume()` now accepts optional `evaluators` and `tools` and preserves the
    configured ones when none are passed, so resumed runs can continue with the
    same behavior as the original run.

## Test Coverage Added

`tests/unit/test_failure_injection.py` covers:

- transient model failure with retry and eventual success
- permanent model failure with terminal failure
- sandbox tool timeout failure
- max iteration budget exhaustion
- max model-call budget exhaustion
- max tool-call budget exhaustion
- corrupt persisted state row graceful degradation
- corrupt latest checkpoint fallback to prior valid checkpoint
- stagnation detection
- checkpoint resume after a simulated mid-run crash

`tests/golden/test_golden_traces.py` covers:

- level 1 refinement event sequence
- level 2 research event sequence
- level 3 coding event sequence

Golden comparisons normalize traces to:

- `event_type`
- `actor`
- `iteration`
- `phase`

Goldens auto-bootstrap when empty and can be force-updated with
`ADK_LOOP_LAB_UPDATE_GOLDEN=1`.

## Verification

Executed successfully:

```bash
PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src/ tests/
PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check src/ tests/
PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache uv run mypy src/
PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ -v
```

Results:

- `ruff check`: passed
- `ruff format --check`: passed
- `mypy src/`: passed
- `pytest tests/ -v`: passed, `152 passed`
