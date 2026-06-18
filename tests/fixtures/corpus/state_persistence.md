# Durable State Persistence

Durable state stores task progress, known facts, and active constraints in a
persistent database such as SQLite. In a long-running workflow, each iteration
reads the latest state before proposing the next action, which makes the state
store the authoritative source of truth. This design survives process restarts
and lets a loop resume after interruption. The trade-off is extra I/O on every
read and write, so teams sometimes cache hot values in memory while keeping the
database as the system of record.
