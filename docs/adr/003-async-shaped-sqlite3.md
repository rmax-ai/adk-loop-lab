# ADR 003: Replace aiosqlite with Async-Shaped sqlite3 Adapters

## Status

Accepted

## Context

The repository originally depended on `aiosqlite` for asynchronous database
access. In practice, the project only needed local SQLite persistence for state
and memory, and the actual I/O pattern was simple and deterministic.

In the Codex sandbox environment, `aiosqlite` introduced hangs and unnecessary
runtime complexity. The project still benefited from async-shaped interfaces,
because the loop controller and example code already use `async` flows.

## Decision

Replace `aiosqlite` usage with thin async-shaped adapters around stdlib
`sqlite3`.

Implementation points:

- `_ConnectionAdapter` and `_CursorAdapter` in
  [src/adk_loop_lab/state/sqlite.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/state/sqlite.py)
- matching adapters in
  [src/adk_loop_lab/memory/sqlite.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/memory/sqlite.py)
- example-local adapter in
  [src/adk_loop_lab/examples/level_3_coding_fleet/example.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/examples/level_3_coding_fleet/example.py)

These adapters preserve the calling shape:

- `await connection.execute(...)`
- `await cursor.fetchone()`
- `await connection.commit()`

without introducing real async database I/O dependencies.

## Consequences

- The code keeps a consistent async surface while relying only on stdlib
  `sqlite3`
- Local persistence works reliably in the sandbox and normal developer
  environments
- The repository no longer depends on `aiosqlite` behavior for correctness
- The async API is cooperative in shape only; it does not provide concurrent
  non-blocking SQLite execution
