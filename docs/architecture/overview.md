# adk-loop-lab Architecture

## Executive Summary

**adk-loop-lab** is an open-source reference implementation that demonstrates
how to build reliable, inspectable agentic loops on top of Google ADK. It
rejects the naive `while not done: call_model()` pattern and instead
implements a controlled state machine: observe → reconstruct context → plan →
execute bounded work → verify → persist evidence → update state → decide
whether to continue.

The core thesis: a useful agentic loop combines **durable state, selective
memory, bounded execution, verification, explicit progress tracking, and
deterministic stopping conditions.**

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLI / ADK Web UI                           │
├──────────────────────────────────────────────────────────────────┤
│                    Loop Controller (deterministic)                │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────────┐ ┌─────────────┐ │
│  │DISCOVER │→│  PLAN   │→│ EXECUTE │→│ VERIFY │→│   COMMIT    │ │
│  └─────────┘ └─────────┘ └─────────┘ └────────┘ └──────┬──────┘ │
│                                                        │        │
│  ┌─────────┐                        ┌───────────────┐   │        │
│  │ DECIDE  │←────────────────────────│   REFLECT     │←──┘        │
│  └────┬────┘                        └───────────────┘            │
│       │                                                          │
│       ├── CONTINUE ──┐                                           │
│       ├── SUCCESS    │  (loop back to DISCOVER)                   │
│       ├── FAILED     │                                           │
│       ├── BLOCKED    │                                           │
│       ├── ESCALATE   │                                           │
│       ├── BUDGET_EXHAUSTED                                       │
│       └── STAGNATED                                              │
└──────────────────────────────────────────────────────────────────┘
         │              │              │
    ┌────▼────┐   ┌─────▼──────┐  ┌───▼──────────┐
    │ State   │   │  Memory    │  │  Events       │
    │ (SQLite)│   │  (SQLite)  │  │  (JSONL)      │
    └─────────┘   └────────────┘  └──────────────┘
```

## Three-Plane Separation

The system separates concerns across three planes:

| Plane | Responsibility | Implementation |
|-------|---------------|----------------|
| **Control Plane** | Loop lifecycle, stopping policies, budget enforcement, checkpointing | Deterministic Python (no model calls) |
| **Execution Plane** | ADK agents, tools, context construction, model invocations | Google ADK + Gemini |
| **Data Plane** | State persistence, event recording, memory storage, artifact management | SQLite + JSONL |

**Key invariant:** The control plane is deterministic. Models influence
direction within an iteration (what to do, how to interpret results), but
deterministic code decides whether the loop continues, stops, or escalates.

## Component Architecture

### Loop Controller (`loop/controller.py`)

The central orchestrator. Manages the lifecycle state machine
(DISCOVER→PLAN→EXECUTE→VERIFY→COMMIT→REFLECT→DECIDE). Invokes ADK agents
and tools at each stage, but owns the state transitions.

**Responsibilities:**
- Iteration lifecycle management
- Budget enforcement (iterations, model calls, tool calls, time)
- Stopping policy evaluation
- Checkpoint coordination
- Recovery from interruption

### ADK Integration Layer (`adk/`)

Thin wrapper around Google ADK APIs. Isolates ADK version sensitivity
behind typed adapters. If ADK APIs change or are unstable, this layer
absorbs the impact.

**Components:**
- `agents.py` — Factory for LlmAgent, LoopAgent, SequentialAgent, ParallelAgent
- `workflows.py` — Reusable workflow patterns (generator-critic, router, fan-out)
- `callbacks.py` — Event emission, state bridging, redaction
- `runner.py` — Runner adapter with timeout, retry, structured output validation
- `compatibility.py` — Version-specific workarounds, deprecation shims

### Context Builder (`context/builder.py`)

Constructs the context for each model invocation. Selects only relevant
information: goal + acceptance criteria + active constraints + current
state + authoritative observations + verified memories + recent failures +
budget status. Emits a context manifest (what was included/excluded, token
estimates) into the trace.

### State Store (`state/`)

Durable key-value/document store backed by SQLite. Supports atomic
transactions, schema-versioned documents, and checkpoint serialization.
In-memory implementation available for tests.

### Memory System (`memory/`)

Vendor-neutral interface for storing and retrieving verified lessons.
Default implementation uses SQLite with FTS5 for text search. Supports
the lifecycle: CANDIDATE → VERIFIED → STALE → INVALIDATED.

### Event System (`events/`)

Append-only event recorder. Writes structured LoopEvent records to JSONL
files. Also provides console display formatting and Mermaid sequence
diagram generation.

### Evaluation System (`evaluation/`)

Deterministic evaluators (schema, lint, tests, constraints) run first.
Model-based evaluators (clarity, coherence, coverage) run only when
deterministic checks pass. Composite evaluator with configurable policies
(DETERMINISTIC_VETO is default).

### Tools (`tools/`)

Sandboxed tools for the coding example. Filesystem operations, shell
execution (allowlisted commands only), patch application, test running.
All tools declare side-effect level and idempotency behavior.

## Request Lifecycle (One Iteration)

```
1. DISCOVER — Read current world state, task state, constraints
   ↓
2. ContextBuilder constructs context manifest
   ↓
3. PLAN — Model proposes bounded action + rationale + verification plan
   ↓
4. EXECUTE — Deterministic dispatch of approved action via tools
   ↓
5. VERIFY — Deterministic evaluators first, model judges if needed
   ↓
6. COMMIT — Atomic state update + checkpoint if verification passed
   ↓
7. REFLECT — Extract verified lessons, record failed approaches
   ↓
8. DECIDE — Deterministic stopping rules applied
   ↓
9. CONTINUE → back to 1, or terminal decision
```

## Trust Boundaries

| # | Boundary | Protects |
|---|----------|----------|
| 1 | **Model ↔ Control Plane** | Model output is advisory only; deterministic code owns state transitions, stopping decisions, tool approval |
| 2 | **Tools ↔ Sandbox** | Coding tools are confined to fixture repo; allowlisted commands; no network; path traversal rejected |
| 3 | **Memory ↔ State** | Memory records require evidence before promotion; state is authoritative |
| 4 | **Secrets ↔ Traces** | Environment variables never appear in event traces; redaction callback strips credentials |
| 5 | **User ↔ Irreversible Operations** | IRREVERSIBLE_WRITE tools require explicit confirmation; READ_ONLY tools are safe by default |

## Policy Model

### Evaluation Policy
- **DETERMINISTIC_VETO** (default): Any failing deterministic evaluator blocks
  success. Model judges can only contribute to scoring.
- **ALL_REQUIRED**: Every evaluator must pass.
- **WEIGHTED_SCORE**: Weighted average with configurable threshold.
- **QUORUM**: Majority of evaluators must pass.

### Stopping Policy
- Max iterations enforced at control-plane level
- Budget exhaustion (model calls, tool calls, time) triggers stop
- Stagnation (no progress for N consecutive iterations) triggers stop
- Success: all acceptance criteria met + all evaluators pass
- Failure: explicit failure detected, no viable recovery path

### Budget Policy
- Tracked per-run: iterations, model calls, tool calls, elapsed time
- Enforcement is deterministic — budgets are checked BEFORE each action
- Budget-exhausted is a terminal decision, not a model recommendation

## Credential Model

- Gemini API key via `GOOGLE_API_KEY` environment variable
- `.env.example` documents required variables
- Secrets never stored in state, memory, or event traces
- Redaction callback strips `GOOGLE_API_KEY` and similar patterns from traces

## Tool Governance

| Category | Examples | Approval | Retry |
|----------|----------|----------|-------|
| READ_ONLY | File read, state query, memory search | Automatic | Yes |
| REVERSIBLE_WRITE | File write (sandboxed), state update | Automatic | Yes |
| IRREVERSIBLE_WRITE | Commit, external API call | Confirmation required | No automatic retry |
| EXECUTION | Shell command (allowlisted) | Confirmation required | Conditional |

## Knowledge and Memory Layer

| Memory Kind | Scope | Promotion | Invalidation |
|-------------|-------|-----------|--------------|
| Lessons learned | Cross-run | Requires evidence | When superseded or contradicted |
| Failed approaches | Cross-run | Automatic (prevents repetition) | Never (historical record) |
| Verified patterns | Cross-run | Requires multiple confirmations | When superseded |
| Run-specific observations | Single run | Not promoted to cross-run | At run completion |

## Observability and Audit

### Captured Events
Every iteration emits events for: lifecycle phase transitions, model calls,
tool invocations, evaluator results, state changes, memory operations,
budget consumption, and stop decisions.

### Trace Outputs
- `var/runs/<run-id>/events.jsonl` — Machine-readable event stream
- `var/runs/<run-id>/run.json` — Run summary
- `var/runs/<run-id>/state.json` — Final state snapshot
- `var/runs/<run-id>/summary.md` — Human-readable summary
- `var/runs/<run-id>/artifacts/` — Generated artifacts
- `var/runs/<run-id>/checkpoints/` — Iteration checkpoints

### Inspection Commands
- `uv run adk-loop inspect <run-id>` — Status, iteration, budgets, evaluations
- `uv run adk-loop events <run-id>` — Full event log

## API and Data Model

### Core Entities
- **LoopRun**: Run metadata, goal, status, budgets, current iteration
- **LoopState**: Facts, constraints, actions, failures, progress score
- **ActionProposal**: Model-generated bounded action with verification plan
- **EvaluationResult**: Evaluator verdict with evidence references
- **MemoryRecord**: Verified lesson or failed approach with evidence
- **LoopEvent**: Append-only event with type, actor, payload, correlation

### Retention
- Runs and their events: retained indefinitely (local files)
- State: SQLite, retained until explicit cleanup
- Memory: SQLite, retained across runs

## Deployment Topology

### Local Development
Single machine. SQLite state + memory. Gemini API via internet.
All three examples run locally.

### Testing (CI)
Fake model adapters replace live Gemini. In-memory state + memory.
All tests pass without credentials.

### Docker (Optional)
`docker-compose.yml` provided as convenience. Not required.

## Risks, Trade-offs, Open Questions

| Risk | Mitigation |
|------|-----------|
| ADK API instability | Compatibility layer in `adk/compatibility.py` |
| Gemini availability | Fake model for testing; configurable model provider |
| SQLite scaling | Interface abstracted; pluggable backends |
| Context window overflow | ContextBuilder with selectors and limits |
| Loop stagnation | Progress detection with N-iteration threshold |
| Model hallucination in verification | Deterministic veto gate overrides model judges |

## Open Questions
- Should memory be per-example or shared across examples?
- Token budget tracking depends on model API availability — may be approximate
- ADK web UI integration depth depends on current ADK version capabilities
