"""ADK callback integration for lifecycle event emission."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from google.adk.agents.context import Context
from google.adk.models.llm_request import LlmRequest

from adk_loop_lab.events.recorder import EventRecorder
from adk_loop_lab.models import EventType, LoopEvent

AdkCallback = Callable[..., Any | None]

_MODEL_CALL_COUNT_KEY = "adk_loop_lab.model_call_count"


def create_event_callback(
    recorder: EventRecorder,
    run_id: str,
    iteration: int,
) -> AdkCallback:
    """Create a before-agent callback that records agent invocation events."""

    def callback(callback_context: Context) -> None:
        agent_name = callback_context.agent_name or callback_context.node_path
        recorder.record(
            LoopEvent(
                run_id=run_id,
                iteration=iteration,
                event_type=EventType.PHASE_ENTER,
                actor=agent_name,
                payload={
                    "callback": "before_agent",
                    "agent_name": agent_name,
                    "node_path": callback_context.node_path,
                    "run_id": callback_context.run_id,
                    "invocation_id": callback_context.invocation_id,
                    "attempt_count": callback_context.attempt_count,
                },
            )
        )

    return callback


def create_model_call_callback(
    recorder: EventRecorder,
    run_id: str,
    iteration: int,
) -> AdkCallback:
    """Create a before-model callback that records model call events."""

    def callback(
        callback_context: Context,
        llm_request: LlmRequest,
    ) -> None:
        prompt_preview = _request_to_text(llm_request)
        model_call_count = int(callback_context.state.get(_MODEL_CALL_COUNT_KEY, 0)) + 1
        callback_context.state[_MODEL_CALL_COUNT_KEY] = model_call_count

        recorder.record(
            LoopEvent(
                run_id=run_id,
                iteration=iteration,
                event_type=EventType.MODEL_CALL,
                actor=callback_context.agent_name or callback_context.node_path,
                payload={
                    "callback": "before_model",
                    "agent_name": callback_context.agent_name,
                    "node_path": callback_context.node_path,
                    "run_id": callback_context.run_id,
                    "invocation_id": callback_context.invocation_id,
                    "model": llm_request.model,
                    "prompt_preview": prompt_preview[:500],
                    "prompt_content_count": len(llm_request.contents),
                    "tool_count": len(llm_request.tools_dict),
                    "model_call_count": model_call_count,
                },
            )
        )

    return callback


def _request_to_text(llm_request: LlmRequest) -> str:
    """Collapse an ``LlmRequest`` into plain text for logging and matching."""
    text_parts: list[str] = []
    for content in llm_request.contents:
        for part in content.parts or []:
            if part.text:
                text_parts.append(part.text)
    return "\n".join(text_parts)
