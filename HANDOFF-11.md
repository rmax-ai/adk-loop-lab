# HANDOFF-11

## What was built

- Added `src/adk_loop_lab/examples/level_3_coding_fleet/agents.py` with:
  - observer, planner, and implementer ADK agents
  - deterministic fake-model responses for repository investigation, bounded
    planning, implementation, and test design

- Added `src/adk_loop_lab/examples/level_3_coding_fleet/orchestrator.py` with:
  - enum-validated routing via `AgentRoute`
  - bounded failure-memory tracking via `FailureRecord`
  - repetition blocking after repeated failed retries
  - sandbox diff collection through `git diff`

- Added `src/adk_loop_lab/examples/level_3_coding_fleet/example.py` with:
  - a resumable Example 3 loop using `LoopController`
  - sandbox setup by copying `tests/fixtures/target_repo/`
  - repository observation, bounded planning, routed implementation, and
    sandboxed pytest verification
  - deterministic evaluators for tests, TTL requirements, and failure-memory
  - fake-model execution that applies TTL support plus TTL-focused tests inside
    the sandbox fixture repo

## Verification

- Pending in this handoff: `uv run ruff check .`
- Pending in this handoff: `uv run mypy src`
- Pending in this handoff:
  `PYTHONPATH=src uv run python3 -c "import asyncio; from adk_loop_lab.examples.level_3_coding_fleet.example import run_example; asyncio.run(run_example(use_fake_model=True))"`

## Notes

- The example keeps control-plane decisions deterministic: ADK agents only
  produce investigation, planning, and implementation text, while routing,
  repetition checks, verification, and stopping remain local code.
- `FailureRecord` uses a dataclass because it is an internal non-validated type;
  public loop state and evaluator outputs still use Pydantic models.
