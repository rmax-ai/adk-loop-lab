# Checkpointing And Resume

Checkpointing records snapshots of workflow state at defined boundaries such as
after each iteration or before expensive tool calls. A checkpoint can include
current facts, completed actions, pending work, and budget counters. When a run
is interrupted, the controller can reload the latest checkpoint and continue
from a known-good state instead of starting from scratch. Checkpoints reduce
lost work, but they need clear policies about frequency and what data is safe to
persist so restore behavior stays deterministic.
