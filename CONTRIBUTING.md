# Contributing to adk-loop-lab

## Development Setup

```bash
git clone https://github.com/rmax-ai/adk-loop-lab.git
cd adk-loop-lab
uv sync
uv run pytest
```

For live ADK or Gemini runs, copy `.env.example` to `.env` and set
`GOOGLE_API_KEY`. Tests should continue to run without live credentials.

## Code Standards

This repository follows the conventions in [AGENTS.md](/home/rmax-10/src/adk-loop-lab/AGENTS.md)
and the Python reference documents in the repo root.

- Keep source code under `src/adk_loop_lab/`
- Add type annotations to all public functions and methods
- Use Pydantic v2 models for validated domain objects
- Keep the control plane deterministic: no model calls in lifecycle, budget, or
  stop-decision logic
- Prefer TDD: add or update tests alongside behavior changes
- Run the quality gates before opening a PR:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

## Project Structure

- `src/adk_loop_lab/loop/`: lifecycle, controller, checkpointing, recovery,
  policies
- `src/adk_loop_lab/adk/`: Google ADK agent factory, runner adapter,
  workflows, compatibility layer
- `src/adk_loop_lab/context/`: per-iteration context assembly via
  `ContextBuilder`
- `src/adk_loop_lab/state/`: authoritative SQLite-backed run and state storage
- `src/adk_loop_lab/memory/`: evidence-gated memory interface and SQLite FTS5
  implementation
- `src/adk_loop_lab/evaluation/`: deterministic and composite evaluators
- `src/adk_loop_lab/events/`: JSONL event recording and console formatting
- `src/adk_loop_lab/examples/`: end-to-end example loops
- `tests/unit/`, `tests/integration/`, `tests/examples/`, `tests/golden/`:
  mirrored validation layers

## Adding a New Example

The current repo ships three examples. A fourth loop should follow the same
shape rather than inventing a separate runtime path.

1. Create a new package under `src/adk_loop_lab/examples/`, following the
   existing layout in
   [src/adk_loop_lab/examples/level_1_refinement/example.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/examples/level_1_refinement/example.py),
   [src/adk_loop_lab/examples/level_2_research/example.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/examples/level_2_research/example.py),
   or
   [src/adk_loop_lab/examples/level_3_coding_fleet/example.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/examples/level_3_coding_fleet/example.py)
2. Reuse `LoopController` from
   [src/adk_loop_lab/loop/controller.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/loop/controller.py)
   instead of creating a custom lifecycle
3. Define explicit budgets with `BudgetConfig`
4. Use fake model adapters or scripts for tests; do not call live Gemini in
   test suites
5. Add matching tests under `tests/examples/` and supporting unit tests under
   `tests/unit/`
6. Add CLI wiring in
   [src/adk_loop_lab/cli.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/cli.py)
   if the example should be runnable from `uv run adk-loop run <example>`
7. Update `README.md` and any relevant concept docs if the example introduces a
   new reusable pattern

## Pull Request Process

- Keep PRs scoped to one coherent change
- Include tests for behavior changes
- Update docs when commands, architecture, or public behavior change
- Prefer small commits with clear intent
- If the change touches ADK integration, keep version-sensitive logic isolated
  in `src/adk_loop_lab/adk/`

PR descriptions should explain:

- What changed
- Why it changed
- How it was verified
- Any follow-up work or known limitations

## Issues

Use GitHub issues for bug reports, feature requests, and documentation gaps.

- Include reproduction steps for bugs
- Identify affected example, module, or command
- Link related traces, failing tests, or fixture data when possible
- For security issues, do not open a public issue; email `me@rmax.io` instead
