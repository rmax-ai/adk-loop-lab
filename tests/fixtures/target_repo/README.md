# KVStore

Simple in-memory key-value store for demonstrating agentic coding loops.

## Task

Add expiration/TTL support: `set(key, value, ttl=None)` where ttl is in seconds.
When ttl is set, the key expires after the specified duration.

Requirements:
- Backward compatible: existing `set(key, value)` calls still work
- `get()` returns None for expired keys
- Expiration is checked on access (lazy), not via background thread
- Add tests for TTL behavior
