# HANDOFF-12

## What was built

- Added [src/adk_loop_lab/config.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/config.py) with:
  - `.env` loading from the current working directory
  - helpers for `GOOGLE_API_KEY`, `ADK_LOOP_STATE_DIR`, and `GOOGLE_MODEL`

- Added [src/adk_loop_lab/cli.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/cli.py) with:
  - `adk-loop examples`
  - `adk-loop run level-1|level-2|level-3 [--offline] [--model] [--max-iterations]`
  - `adk-loop inspect <run-id>` backed by the persisted SQLite state stores
  - `adk-loop events <run-id>` backed by the JSONL event recorder

- Updated the example runners and agent factories so the CLI can pass:
  - per-run `model_name`
  - per-run `max_iterations`
  - consistent state and event output paths under the configured state dir

- Added shell entrypoints:
  - [scripts/run_example_1.sh](/home/rmax-10/src/adk-loop-lab/scripts/run_example_1.sh)
  - [scripts/run_example_2.sh](/home/rmax-10/src/adk-loop-lab/scripts/run_example_2.sh)
  - [scripts/run_example_3.sh](/home/rmax-10/src/adk-loop-lab/scripts/run_example_3.sh)

- Added [Makefile](/home/rmax-10/src/adk-loop-lab/Makefile) with install, lint, format, typecheck, test, examples, and clean targets.

- Added [tests/unit/test_cli_config.py](/home/rmax-10/src/adk-loop-lab/tests/unit/test_cli_config.py) to cover:
  - `.env`-based config loading
  - CLI example listing
  - unknown-example error handling

## Verification

- Verified: `UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src uv run adk-loop examples`
- Verified: `UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src uv run adk-loop run level-1`
- Verified: `UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src uv run adk-loop run level-2`
- Verified: `UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src uv run adk-loop run level-3`
- Verified: `bash scripts/run_example_1.sh`
- Verified: `UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src uv run pytest tests/ -v` → `139 passed`
- Verified: `UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src uv run ruff check src/ tests/`
- Verified: `UV_CACHE_DIR=/tmp/uv-cache PYTHONPATH=src uv run mypy src/`
- Not runnable in this sandbox as `make test`: `/home/rmax-10/.local/bin/make` is a Sphinx-specific shim, not GNU Make. The repository [Makefile](/home/rmax-10/src/adk-loop-lab/Makefile) test recipe is present and matches the verified pytest command above.

## Notes

- `inspect` scans all `*.db` files under `<state_dir>/state/`, which matches the current per-example SQLite layout.
- `events` reads `<state_dir>/runs/<run_id>/events.jsonl`, which already matches the existing recorder implementation.
- The SQLite-backed state and memory stores now use async-shaped `sqlite3` adapters instead of `aiosqlite`; this preserves the public async API while avoiding the `aiosqlite` hangs encountered in this environment.
