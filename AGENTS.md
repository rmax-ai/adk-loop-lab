# AGENTS.md — Guidelines for adk-loop-lab

This document captures conventions for all contributors and AI coding agents
working on **adk-loop-lab**.

---

## 1. Project DNA

- **Language:** Python 3.11+
- **Framework:** Google ADK (latest stable) — never invent ADK APIs
- **Model provider:** Gemini (runtime) / fake adapters (tests)
- **Package manager:** uv
- **Validation:** pydantic v2
- **Layout:** `src/` layout — `src/adk_loop_lab/`
- **License:** MIT

## 2. Code Organization

- All source under `src/adk_loop_lab/`
- Module boundaries match the architecture: `loop/`, `adk/`, `context/`, `memory/`,
  `state/`, `events/`, `evaluation/`, `tools/`, `models/`, `examples/`
- `__init__.py` re-exports public API only
- Single responsibility per module
- Imports: stdlib → third-party → first-party, alphabetically within each group

## 3. Error Handling

- Use `Result` pattern or explicit exceptions — never swallow errors silently
- Model output must be validated against Pydantic schemas before use
- Recovery policies are explicit: bounded retries with backoff for transient
  failures, no retry for deterministic failures without changing the action
- Log errors at appropriate level before propagating

## 4. Python Conventions

- Type annotations on ALL public functions and methods
- Pydantic v2 models for all domain objects (use `model_config`, not `Config`
  inner class)
- Dataclasses only for internal/non-validated types
- `async/await` for ADK interactions; sync for deterministic control plane
- No mutable default arguments
- Use `ClassVar` for class-level mutable state (RUF012)

## 5. Testing

- Tests in `tests/` mirroring `src/` structure
- Unit tests: `tests/unit/` — fast, no I/O, fake adapters
- Integration tests: `tests/integration/` — real SQLite, fake models
- Example tests: `tests/examples/` — full loop with fake models
- Goldens: `tests/golden/` — event traces for representative runs
- Fixtures: `tests/fixtures/` — corpus docs, target repos
- Test what the code does, not how it does it
- For ADK: test with fake model adapters (never call live Gemini in tests)

## 6. Documentation

- Public API: Google-style docstrings with type hints
- README: updated when commands or architecture change
- `docs/concepts/`: conceptual explanations (loop engineering, state vs memory, etc.)
- `docs/architecture/`: system design docs
- `docs/tutorials/`: per-example walkthroughs
- `docs/adr/`: architecture decision records

## 7. Dependencies

- All dependencies in `pyproject.toml` with version pins
- `uv.lock` committed to repo
- No optional dependency should be required for core functionality
- Fake model adapters: in-tree, no external mock libraries
- Semantic memory: interface defined, no mandatory implementation

## 8. Formatting and Linting

```bash
uv run ruff check .        # lint
uv run ruff format --check .  # format check
uv run mypy src            # type check
```

- ruff rules: I (isort), F (pyflakes), E/W (pycodestyle), N (pep8-naming),
  UP (pyupgrade), B (flake8-bugbear), RUF (ruff-specific)
- Line length: 100
- mypy: strict mode

## 9. Architecture Non-Negotiables

- **Control plane is deterministic.** No model calls in loop lifecycle,
  budget enforcement, stopping decisions.
- **State is authoritative.** Read current state each iteration; don't trust
  model memory for facts.
- **Verification before promotion.** Memory records require evidence.
- **Bounded iteration.** Every loop has max iterations, max duration,
  model-call budget, tool-call budget.
- **ADK isolation.** ADK API calls go through `adk/compatibility.py` or
  adapter layer. Never call ADK directly from loop controller.
- **Security by default.** Shell tools: allowlisted commands only. No secrets
  in traces. Path confinement in sandbox.

## 10. References

- [PYTHON_DEVELOPMENT.md](PYTHON_DEVELOPMENT.md) — Day-to-day Python
- [PYTHON_API_DESIGN.md](PYTHON_API_DESIGN.md) — API surface design
- [PYTHON_SYSTEM_DESIGN_PATTERNS.md](PYTHON_SYSTEM_DESIGN_PATTERNS.md) —
  Patterns: actor model, pipeline, circuit breaker, etc.
- [PYTHON_ARCHITECTURE.md](PYTHON_ARCHITECTURE.md) — Package layout and
  module boundaries
