# HANDOFF-4

## What was built

- `src/adk_loop_lab/adk/workflows.py`
  - Added graph-based helpers for sequential and parallel workflow construction using ADK `Workflow(edges=...)`.
  - Added a generator/critic workflow helper that inserts a small routing node to support bounded refinement loops without deprecated ADK workflow agents.

- `src/adk_loop_lab/adk/callbacks.py`
  - Added `create_event_callback()` for `before_agent_callback` event recording.
  - Added `create_model_call_callback()` for `before_model_callback` recording, including lightweight state-based model-call counting.

- `src/adk_loop_lab/adk/fake_model.py`
  - Added `make_fake_response()` for building ADK-compatible canned `LlmResponse` objects.
  - Added a default `before_model_callback()` that can serve responses from state-backed script entries.
  - Added `FakeModelScript` for fragment-based scripted responses with first-match-wins behavior.

## Verification completed

- Ran the requested Batch 2 smoke script with `PYTHONPATH=src`.
- Ran `uv run ruff check src`.
- Ran `uv run mypy src`.

## Decisions made

- The installed ADK 2.2.0 callback signature for `before_model_callback` is `(Context, LlmRequest) -> LlmResponse | None`.
  - `google.adk.agents.callback_context.CallbackContext` is an alias of `Context` in this version.

- The generator/critic helper uses a routing node instead of a direct `critic -> END` edge.
  - ADK 2.2.0 graph workflows terminate by reaching a terminal node; there is no public `END` sentinel to target in `edges=...`.
  - The router stops on a simple approval heuristic or when `max_rounds` is reached, otherwise it routes back to the generator.

- Model-call tracking is state-backed and local to the callback context.
  - The callback stores a counter under `adk_loop_lab.model_call_count` so later budget orchestration can read it without parsing recorder output.

## What Phase 5 should know

- `generator_critic_workflow()` currently uses text heuristics to detect critic approval.
  - If Phase 5 introduces structured critic outputs, update the router to inspect those explicit fields instead of free text.

- `create_event_callback()` maps agent invocation into `EventType.PHASE_ENTER`.
  - If the event taxonomy grows an agent-specific lifecycle event, switch this callback to the more precise type.

- `FakeModelScript` supports partial mocking.
  - Unmatched prompts return `None`, which allows the configured real model path to run if a caller mixes scripted and real behavior.
