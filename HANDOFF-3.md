# HANDOFF-3

## What was built

- `src/adk_loop_lab/adk/compatibility.py`
  - Added ADK version detection with a direct `google.adk.__version__` lookup and package-metadata fallback.
  - Added `require_adk_version()` with the Batch 1 minimum of `2.2.0`.
  - Added `get_default_model()` pinned to ADK v2.2.0's `gemini-3-flash-preview`.

- `src/adk_loop_lab/adk/agents.py`
  - Added `create_agent()` as the standard factory for `google.adk.Agent` / `LlmAgent`.
  - Centralizes default model selection and common configuration for tools, output key, and output schema.

- `src/adk_loop_lab/adk/runner.py`
  - Added `create_runner()` returning an ADK `InMemoryRunner`.
  - Added `run_agent()` that ensures the session exists, sends a user message with the ADK v2 `types.Content` shape, and collects non-thought text from streamed events.
  - Added `adk_event_to_loop_event()` to wrap raw ADK events in the repo's `LoopEvent` envelope.

## Verification completed

- Ran the requested adapter smoke test with `PYTHONPATH=src`.
- Ran `uv run ruff check src`.
- Ran `uv run mypy src`.

## Decisions made

- `create_runner()` uses `InMemoryRunner(agent=..., app_name=...)` directly.
  - ADK 2.2.0's convenience runner no longer accepts `session_service=` in its constructor; it creates its own in-memory services internally.

- `run_agent()` creates a session only when one does not already exist.
  - This keeps repeated calls with the same `session_id` from failing on duplicate session creation.

- User input is sent as `google.genai.types.Content`.
  - ADK 2.2.0 `run_async()` expects structured content, not a raw string.

## What Story 4.2 Batch 2 should know

- Keep ADK API calls isolated under `src/adk_loop_lab/adk/`.
  - This batch intentionally contains the version-sensitive pieces so later loop orchestration should depend on these adapters, not on `google.adk` directly.

- `adk_event_to_loop_event()` currently maps every incoming ADK event to `EventType.MODEL_CALL`.
  - Batch 2 can refine this once it decides which ADK event patterns matter for model responses, tool calls, and lifecycle transitions.

- `run_agent()` currently returns concatenated visible text from non-partial events.
  - If Batch 2 needs stricter "final response only" semantics, it should key off additional ADK event metadata instead of changing call sites to parse ADK events directly.
