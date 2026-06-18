# HANDOFF-7

## What was built

- `src/adk_loop_lab/memory/base.py`
  - Added the vendor-neutral `MemoryStore` abstract interface with lifecycle methods for initialize, add, get, search, promote, invalidate, and close.

- `src/adk_loop_lab/memory/sqlite.py`
  - Added `SqliteMemoryStore` backed by `aiosqlite`.
  - Persists `MemoryRecord` values as JSON in `memory_records`.
  - Maintains an `FTS5` virtual table `memory_fts` over record content for text search.
  - Supports candidate promotion and invalidation by updating the stored record and keeping FTS rows in sync.

- `src/adk_loop_lab/memory/promotion.py`
  - Added `MemoryPromoter` for evidence-gated promotion, candidate creation, staleness marking, and supersession invalidation.

## Verification completed

- Ran `uv run ruff check src HANDOFF-7.md`.
- Ran `uv run mypy src`.
- Attempted the requested `PYTHONPATH=src uv run python3 -c "...Story 5.3..."` smoke verification, but `aiosqlite.connect()` hangs in this sandbox.
  - Confirmed the same hang with the pre-existing `src/adk_loop_lab/state/sqlite.py` path, so this is environmental rather than specific to the new memory store.

## Decisions made

- `SqliteMemoryStore.add()` uses upsert semantics keyed by `memory_id` so lifecycle transitions such as `STALE` can remain vendor-neutral and flow through the same store interface.
- Empty-query `search()` falls back to filtered recency listing instead of FTS `MATCH`, which avoids SQLite FTS syntax issues and supports promoter workflows.

## Follow-up considerations

- If a future in-memory test backend is added, it should match the upsert behavior used here for lifecycle updates.
- If promotion rules later require stronger provenance, the promoter can enforce structured evidence metadata instead of raw string references.
