# HANDOFF-10

## What was built

- Added `tests/fixtures/target_repo/`, a compact Python fixture repository with:
  - `kvstore.py` implementing the baseline in-memory key-value store.
  - `tests/test_kvstore.py` covering set/get/delete/exists/keys behavior.
  - `README.md` describing the future TTL task for Example 3.

- Added `src/adk_loop_lab/tools/` with:
  - `filesystem.py` for sandbox-confined file reads, writes, existence checks,
    and directory listing.
  - `shell.py` for allowlisted command execution with path validation, timeout
    handling, environment sanitization, and output truncation.
  - `safety.py` defining shared side-effect metadata and default tool specs.
  - `__init__.py` re-exporting the public sandbox tool surface.

- Added `tests/unit/test_tools.py` covering:
  - Filesystem path traversal rejection.
  - Allowlist enforcement in `SandboxShell`.
  - Shell timeout handling and output truncation.
  - Safety metadata on `TOOL_SPECS`.

## Verification

- Passed: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit/test_tools.py tests/fixtures/target_repo/tests`
- Passed: `PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache uv run python3 -c "...sandbox verification snippet..."`
- Passed: `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`
- Passed: `UV_CACHE_DIR=/tmp/uv-cache uv run mypy src`
- Repo caveat: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest` stalls at
  `tests/examples/test_level_1_refinement.py::test_run_example_fake_model`,
  which appears unrelated to the sandbox-tool changes in this batch.

## Notes

- `SandboxFilesystem.write()` is implemented because Batch 2 will need reversible
  edits inside the target repo, even though the default posture remains confined
  access under a single sandbox root.
- `SandboxShell` uses `subprocess.run(..., shell=False)` via argv parsing, so
  shell metacharacters are not interpreted as operators.
