# adk-loop-lab — Specification

## Scope

An open-source reference implementation demonstrating loop engineering with
Google ADK. Shows the transition from prompting an agent → wrapping it in a
harness → operating through a controlled loop. The repository serves as both
a working demonstration and a reusable starter kit.

## Core Thesis

A useful agentic loop combines durable state, selective memory, bounded
execution, verification, explicit progress tracking, and deterministic
stopping conditions.

## Design Principles

1. **Deterministic shell, probabilistic core** — Models propose; deterministic
   code decides
2. **Authoritative state before remembered state** — Read current facts each
   iteration
3. **Bounded iteration** — Every loop has explicit max iterations, budgets,
   and stopping conditions
4. **Verification before memory promotion** — Evidence required before
   learning
5. **Inspectability** — Every iteration exposes state, actions, evaluations,
   and decisions
6. **Idempotency and resume** — Checkpoint after each iteration; support
   interruption recovery
7. **Educational clarity** — Explicit architecture over clever abstractions

## Features

### Loop Controller
- Lifecycle state machine: DISCOVER → PLAN → EXECUTE → VERIFY → COMMIT →
  REFLECT → DECIDE
- Budget enforcement (iterations, model calls, tool calls, time)
- Stopping policies (SUCCESS, FAILED, BLOCKED, BUDGET_EXHAUSTED, STAGNATED)
- Checkpointing and resume
- Progress and stagnation detection
- Recovery policies for model/tool/timeout failures

### ADK Integration
- Agent factory (Gemini as default)
- Workflow construction (Workflow graph API)
- Runner adapter with structured output validation
- Callback integration (state bridging, event emission, redaction)
- Fake model adapter for testing
- Compatibility layer for ADK version changes

### Context Construction
- Selective context building per iteration
- Configurable selectors with limits
- Context manifests in traces

### Verification Subsystem
- Deterministic evaluators (schema, lint, tests, constraints)
- Model-based evaluators (clarity, coherence, coverage)
- Composite evaluator with DETERMINISTIC_VETO default
- Evaluation results with evidence references

### Memory System
- Vendor-neutral interface
- SQLite default with FTS5 search
- CANDIDATE → VERIFIED → STALE → INVALIDATED lifecycle
- Evidence-gated promotion

### Event System
- Append-only JSONL event recorder
- 30 event types across full lifecycle
- Console display formatting
- Trace inspection commands

### Reusable Patterns
- Sequential stage
- Iterative refinement loop
- Parallel fan-out and aggregation
- Routing (enum-validated dispatch)
- Generator–critic
- Plan–execute–replan
- Tool-use boundary with side-effect classification

### Three Examples
1. **Level 1: Bounded document refinement** — Generator-critic loop with
   word count, style checks, max 5 iterations
2. **Level 2: Evidence-driven research** — Parallel source research,
   claim-evidence matrix, gap-driven iteration, citation verification
3. **Level 3: Resumable coding loop** — Sandboxed multi-agent coding with
   parallel evaluators, failure memory, interrupt/resume

### Developer UX
- CLI: `adk-loop run/examples/inspect/events/reset-example`
- ADK web UI compatibility
- Shell scripts for one-click example runs
- Trace viewer

## Acceptance Criteria

### Phase 1-3 — Foundation
- [ ] Project bootstraps with `uv sync`
- [ ] All domain models have Pydantic schemas and tests
- [ ] ADK imports verified (Agent, Workflow, BaseAgent, Runner)
- [ ] GitHub repo with labels and issues
- [ ] `uv run ruff check .` passes
- [ ] `uv run ruff format --check .` passes
- [ ] `uv run mypy src` passes
- [ ] `uv run pytest` passes

### Phase 4-5 — ADK + Loop Blocks
- [ ] Loop controller runs full lifecycle
- [ ] Budget enforcement prevents unbounded execution
- [ ] Checkpoint + resume works
- [ ] ADK agents can be constructed and run
- [ ] Fake model adapter works for all loop patterns
- [ ] Context builder produces manifests
- [ ] All reusable patterns have tests

### Phase 6 — Example 1
- [ ] Refinement loop runs with fake model
- [ ] Word count check passes (180-260 words)
- [ ] Style checks pass
- [ ] Max 5 iterations enforced
- [ ] Event traces valid

### Phase 7 — Example 2
- [ ] Research loop runs with fixture corpus
- [ ] Parallel source research works
- [ ] Claim-evidence matrix generated
- [ ] Gap-driven iteration works
- [ ] Citation verification passes
- [ ] Report generated with traceable citations

### Phase 8 — Example 3
- [ ] Coding loop runs against fixture repo
- [ ] Sandbox tools confined (allowlisted commands, no network)
- [ ] Parallel evaluators work
- [ ] Failure memory prevents repeated equivalent patches
- [ ] Interrupt and resume works
- [ ] All quality gates pass (tests, lint, type check)

### Phase 9 — Developer UX
- [ ] All CLI commands work
- [ ] Examples run from CLI
- [ ] Inspection shows state, evaluations, stop decision
- [ ] Shell scripts work

### Phase 10 — Hardening
- [ ] Failure injection tests pass
- [ ] Golden event traces match
- [ ] Clean-room setup test passes
- [ ] All documentation current
- [ ] SECURITY.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md present
