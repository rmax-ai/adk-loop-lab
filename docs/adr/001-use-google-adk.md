# ADR 001: Use Google ADK

## Status

Accepted

## Context

`adk-loop-lab` is a reference implementation for loop engineering, not a
general-purpose agent framework. The project needed:

- a concrete runtime for Gemini-based agent execution
- support for workflow composition patterns
- a runner suitable for tests and examples
- isolation from vendor API churn in the loop controller itself

The main alternatives were:

- raw Gemini SDK calls everywhere
- LangChain as the orchestration surface
- Google ADK with an internal compatibility layer

Raw Gemini SDK calls would have reduced framework dependency but would also
have forced agent execution, workflow composition, and runtime session handling
to spread across the codebase. LangChain would have introduced a larger and
less project-specific abstraction surface than this repository needs.

## Decision

Use Google ADK as the execution framework and isolate all ADK-sensitive code in
the `src/adk_loop_lab/adk/` package.

Key implementation points:

- agent construction in
  [src/adk_loop_lab/adk/agents.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/adk/agents.py)
- workflow helpers in
  [src/adk_loop_lab/adk/workflows.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/adk/workflows.py)
- runner adapter using `InMemoryRunner` in
  [src/adk_loop_lab/adk/runner.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/adk/runner.py)
- version checks and defaults in
  [src/adk_loop_lab/adk/compatibility.py](/home/rmax-10/src/adk-loop-lab/src/adk_loop_lab/adk/compatibility.py)

The loop controller remains ADK-agnostic and only interacts through callables
and typed models.

## Consequences

- The project uses ADK's workflow graph API rather than inventing its own
  execution graph runtime
- The examples can run through `google.adk.runners.InMemoryRunner`, which keeps
  local runs and tests lightweight
- ADK version-sensitive behavior is centralized, but the repo remains exposed
  to upstream API changes at the adapter boundary
- The project is opinionated toward Gemini and ADK, which improves clarity for
  the reference implementation but reduces framework neutrality
