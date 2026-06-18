# HANDOFF-14

## Summary

Phase 10.2 documentation work is complete.

Created:

- `SECURITY.md`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `docs/concepts/loop-engineering.md`
- `docs/concepts/context-vs-state-vs-memory.md`
- `docs/concepts/verification-and-stopping.md`
- `docs/concepts/failure-modes.md`
- `docs/adr/001-use-google-adk.md`
- `docs/adr/002-sqlite-not-vector-db.md`
- `docs/adr/003-async-shaped-sqlite3.md`

Updated:

- `README.md`

## Notes

- The concept docs reference actual modules and current APIs from `src/`
- `README.md` was limited to the requested status section and verified version
  table update
- `CODE_OF_CONDUCT.md` uses Contributor Covenant 2.1 with `me@rmax.io` as the
  enforcement contact

## Verification

Run:

```bash
PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache uv run ruff check src/ tests/
PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache uv run ruff format --check src/ tests/
PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache uv run mypy src/
PYTHONPATH=src UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/ -v
```
