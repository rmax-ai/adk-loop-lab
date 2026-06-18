# ADR 002: Use SQLite FTS5 Instead of a Vector Database

## Status

Accepted

## Context

The memory subsystem in `adk-loop-lab` needed durable storage, text search, and
clear evidence tracking without requiring hosted infrastructure or vendor
lock-in.

The project goals favored:

- local-first development
- no mandatory external service for core functionality
- inspectable persistence that works in tests and examples
- memory promotion rules based on evidence, not only semantic similarity

Alternatives considered included managed vector databases, embedded vector
stores, or custom semantic pipelines as the default memory backend.

## Decision

Use SQLite FTS5 as the default memory implementation, with evidence-gated
promotion and a pluggable interface for future backends.

Implementation points:

- abstract interface in
  [src/adk_loop_lab/memory/base.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/memory/base.py)
- default store in
  [src/adk_loop_lab/memory/sqlite.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/memory/sqlite.py)
- promotion lifecycle in
  [src/adk_loop_lab/memory/promotion.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/memory/promotion.py)
- record model in
  [src/adk_loop_lab/models/memory.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/models/memory.py)

Memory promotion remains explicit:

- new records start as `CANDIDATE`
- promotion to `VERIFIED` requires evidence references
- stale or superseded knowledge can be marked `STALE` or `INVALIDATED`

## Consequences

- Core memory works with no external service and no vendor lock-in
- Full-text search is lexical, not semantic, out of the box
- The system gains inspectability and easy local testing at the cost of missing
  built-in embedding similarity search
- Future semantic backends remain possible because the store is abstracted
  behind `MemoryStore`
