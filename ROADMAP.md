# Roadmap

## Phase 1 — Bootstrap ✅ (current)

- [ ] Initialize project with `uv init`
- [ ] Configure `pyproject.toml` with dependencies
- [ ] Pin verified Google ADK version
- [ ] Add linting (ruff), typing (mypy), and test (pytest) configuration
- [ ] Add `.env.example` with `GOOGLE_API_KEY`
- [ ] Add `.gitignore`
- [ ] Verify: `uv sync`, `uv run ruff check .`, `uv run mypy src`, `uv run pytest`

**Estimated Codex sessions:** 1-2

---

## Phase 2 — Domain Contracts

- [ ] `src/adk_loop_lab/models/state.py` — LoopState, LoopRun
- [ ] `src/adk_loop_lab/models/events.py` — LoopEvent, event types
- [ ] `src/adk_loop_lab/models/plans.py` — ActionProposal
- [ ] `src/adk_loop_lab/models/evaluations.py` — EvaluationResult
- [ ] `src/adk_loop_lab/models/budgets.py` — Budget models, enforcement
- [ ] Storage interfaces: StateStore, MemoryStore, EventRecorder

**Estimated Codex sessions:** 1-2

---

## Phase 3 — Runtime Foundation

- [ ] `src/adk_loop_lab/events/recorder.py` — JSONL event recorder
- [ ] `src/adk_loop_lab/events/console.py` — Console display
- [ ] `src/adk_loop_lab/state/sqlite.py` — SQLite state store
- [ ] `src/adk_loop_lab/state/transactions.py` — Atomic transactions
- [ ] `src/adk_loop_lab/loop/checkpoints.py` — Checkpoint manager
- [ ] `src/adk_loop_lab/loop/policies.py` — Budget manager
- [ ] `src/adk_loop_lab/loop/stopping.py` — Stopping-policy engine
- [ ] `src/adk_loop_lab/loop/recovery.py` — Recovery policy

**Estimated Codex sessions:** 2-3

---

## Phase 4 — ADK Adapters

- [ ] `src/adk_loop_lab/adk/agents.py` — Model agent factory
- [ ] `src/adk_loop_lab/adk/workflows.py` — Workflow agent construction
- [ ] `src/adk_loop_lab/adk/runner.py` — Runner adapter
- [ ] `src/adk_loop_lab/adk/callbacks.py` — Callback integration
- [ ] `src/adk_loop_lab/adk/compatibility.py` — Version compatibility layer
- [ ] State bridge between ADK session state and LoopState
- [ ] Fake model adapter for testing

**Estimated Codex sessions:** 2-3
**Dependencies:** Phase 2 (domain models), Phase 3 (runtime)

---

## Phase 5 — Reusable Loop Blocks

- [ ] `src/adk_loop_lab/loop/controller.py` — Main loop controller
- [ ] `src/adk_loop_lab/loop/lifecycle.py` — Lifecycle state machine
- [ ] Sequential stage (ADK SequentialAgent)
- [ ] Refinement loop (LoopAgent or custom BaseAgent)
- [ ] Parallel fan-out and aggregation (ParallelAgent)
- [ ] Router (enum-validated dispatch)
- [ ] Generator–critic pattern
- [ ] Plan–execute–replan pattern
- [ ] `src/adk_loop_lab/context/builder.py` — Context builder
- [ ] `src/adk_loop_lab/context/selectors.py` — Context selectors
- [ ] `src/adk_loop_lab/evaluation/deterministic.py` — Deterministic evaluators
- [ ] `src/adk_loop_lab/evaluation/model_judge.py` — Model-based evaluators
- [ ] `src/adk_loop_lab/evaluation/composite.py` — Composite evaluator
- [ ] `src/adk_loop_lab/evaluation/progress.py` — Progress and stagnation detection
- [ ] `src/adk_loop_lab/memory/base.py` — Memory interface
- [ ] `src/adk_loop_lab/memory/sqlite.py` — SQLite memory
- [ ] `src/adk_loop_lab/memory/in_memory.py` — In-memory memory (tests)
- [ ] `src/adk_loop_lab/memory/promotion.py` — Memory promotion logic

**Estimated Codex sessions:** 4-6
**Dependencies:** Phase 3, Phase 4

---

## Phase 6 — Example 1: Bounded Document Refinement Loop

- [ ] `src/adk_loop_lab/examples/level_1_refinement/` — Example package
- [ ] DraftAgent, CriticAgent, RevisionAgent
- [ ] DeterministicChecks (word count, style, citation)
- [ ] StopGate with max 5 iterations
- [ ] Event tracing for each revision
- [ ] Checkpointing after each iteration
- [ ] Unit tests with fake model responses
- [ ] `scripts/run_example_1.sh`
- [ ] `docs/tutorials/example-1.md`

**Estimated Codex sessions:** 2-3
**Dependencies:** Phase 5

---

## Phase 7 — Example 2: Evidence-Driven Research Loop

- [ ] `src/adk_loop_lab/examples/level_2_research/` — Example package
- [ ] Fixture corpus in `tests/fixtures/corpus/`
- [ ] CorpusDiscoveryAgent, ResearchPlanner, EvidenceAggregator
- [ ] ParallelAgent for source researchers
- [ ] GapEvaluator with claim–evidence matrix
- [ ] CitationVerifier
- [ ] ReportWriter
- [ ] Max 4 research iterations
- [ ] `scripts/run_example_2.sh`
- [ ] `docs/tutorials/example-2.md`

**Estimated Codex sessions:** 3-4
**Dependencies:** Phase 6 (reuses loop blocks)

---

## Phase 8 — Example 3: Resumable Multi-Agent Coding Loop

- [ ] `src/adk_loop_lab/examples/level_3_coding_fleet/` — Example package
- [ ] Fixture repository in `tests/fixtures/target_repo/` (in-memory KV store)
- [ ] RepositoryObserver, TaskPlanner, Router
- [ ] Specialist agents: CodeInvestigator, TestDesigner, ImplementationAgent
- [ ] `src/adk_loop_lab/tools/` — Sandboxed tools
  - [ ] `filesystem.py` — Read-only filesystem operations
  - [ ] `shell.py` — Allowlisted shell commands with sandboxing
  - [ ] `patch.py` — Patch application
  - [ ] `tests.py` — Test runner
  - [ ] `safety.py` — Path confinement, timeout, output caps
- [ ] ParallelAgent for evaluators (UnitTest, Lint, TypeCheck, Requirements)
- [ ] FailureClassifier
- [ ] Replanner
- [ ] FinalReviewer + CommitGate
- [ ] Isolated worktrees for parallel makers
- [ ] Resume support (interrupt and continue)
- [ ] Failed-attempt memory to prevent repeating equivalent patches
- [ ] `scripts/run_example_3.sh`
- [ ] `docs/tutorials/example-3.md`

**Estimated Codex sessions:** 4-6
**Dependencies:** Phase 7 (reuses evaluation, memory, routing)

---

## Phase 9 — Developer UX

- [ ] `src/adk_loop_lab/cli.py` — CLI with all commands
- [ ] `src/adk_loop_lab/config.py` — Configuration loading
- [ ] ADK web UI compatibility (if supported by current ADK version)
- [ ] Trace viewer / `inspect_trace.py`
- [ ] `scripts/run_example_*.sh` — One-click example runners
- [ ] Sample output files in `var/`
- [ ] `Makefile` — Common operations

**Estimated Codex sessions:** 2-3
**Dependencies:** Phase 6-8 (examples must exist)

---

## Phase 10 — Hardening

- [ ] Failure injection tests (malformed model output, tool timeout, etc.)
- [ ] Security tests (secrets in traces, path traversal, network access)
- [ ] Golden event traces for representative runs
- [ ] Documentation review and completeness check
- [ ] Final clean-room setup test (clone → install → run all examples)
- [ ] `CONTRIBUTING.md`
- [ ] `SECURITY.md`
- [ ] `CODE_OF_CONDUCT.md`
- [ ] Verify all quality gates pass

**Estimated Codex sessions:** 2-3
**Dependencies:** Phase 9

---

## Future (post v1.0)

- [ ] Semantic embedding memory adapter (optional, vendor-neutral)
- [ ] Docker Compose convenience setup
- [ ] Mermaid sequence diagram generation from event traces
- [ ] Additional example loops contributed by community
- [ ] Support for non-Gemini model providers
- [ ] Web dashboard for run inspection
