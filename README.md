# adk-loop-lab

**A reference implementation demonstrating loop engineering with Google ADK.**

> A useful agentic loop combines durable state, selective memory, bounded
> execution, verification, explicit progress tracking, and deterministic
> stopping conditions.

## Quick Start

```bash
git clone https://github.com/rmax-ai/adk-loop-lab.git
cd adk-loop-lab

# Install dependencies
uv sync

# Configure Gemini
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# Run the examples
uv run adk-loop run level-1    # Bounded document refinement
uv run adk-loop run level-2    # Evidence-driven research
uv run adk-loop run level-3    # Resumable coding loop

# Run tests (no credentials needed)
uv run pytest
```

## Architecture

```
DISCOVER → PLAN → EXECUTE → VERIFY → COMMIT → REFLECT → DECIDE
    ↑                                                      │
    └──────────────────────────────────────────────────────┘
                    (CONTINUE only)
```

Three planes:
- **Control Plane** — Deterministic loop lifecycle, budgets, stopping
- **Execution Plane** — ADK agents, Gemini models, tools
- **Data Plane** — SQLite state, JSONL events, memory records

See [`docs/architecture/overview.md`](docs/architecture/overview.md) for the full architecture.

## Three Examples

| Example | Level | Concept |
|---------|-------|---------|
| [Document Refinement](docs/tutorials/example-1.md) | 1 | Generator–critic loop with deterministic stopping |
| [Evidence Research](docs/tutorials/example-2.md) | 2 | Parallel research, evidence tracking, gap-driven iteration |
| [Coding Fleet](docs/tutorials/example-3.md) | 3 | Resumable multi-agent coding with sandboxed tools |

## Core Concepts

- **Loop Engineering** — Designing the outer control system that reconstructs
  context, invokes agents, verifies outcomes, persists state, and decides
  what happens next.

- **State vs Memory** — State is authoritative and read fresh each iteration.
  Memory is promoted only after verification with evidence.

- **Deterministic Shell** — Models propose; deterministic code decides.
  Stopping conditions, budget enforcement, and tool approval never depend on
  model output.

- **Verification First** — Deterministic evaluators (schema, lint, tests) run
  before model judges. Deterministic failures always veto success.

See [`docs/concepts/`](docs/concepts/) for in-depth explanations.

## Development

```bash
# Lint
uv run ruff check .

# Format check
uv run ruff format --check .

# Type check
uv run mypy src

# Tests
uv run pytest

# All quality gates
uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest
```

## Dependencies

- Python 3.11+
- Google ADK (latest stable)
- Gemini API
- SQLite (stdlib)
- uv (package management)

## Verified Versions

| Dependency | Version | Notes |
|-----------|---------|-------|
| Python | TBD | 3.11+ required |
| google-adk | TBD | Pinned after API verification |
| pydantic | TBD | |
| pytest | TBD | |
| ruff | TBD | |
| mypy | TBD | |

## Documentation

- [Architecture Overview](docs/architecture/overview.md)
- [Loop Engineering](docs/concepts/loop-engineering.md)
- [Context vs State vs Memory](docs/concepts/context-vs-state-vs-memory.md)
- [Verification and Stopping](docs/concepts/verification-and-stopping.md)
- [Failure Modes](docs/concepts/failure-modes.md)
- [Architecture Decision Records](docs/adr/)

## License

MIT — see [LICENSE](LICENSE).

## Limitations

- Default memory uses SQLite FTS5 (no vector embeddings)
- Gemini is the only tested model provider
- Coding sandbox is Linux-only (shell commands)
- ADK web UI integration depends on current ADK version
- Token budget tracking is approximate (depends on model API)

## Roadmap

See [ROADMAP.md](ROADMAP.md) for the phased implementation plan.
