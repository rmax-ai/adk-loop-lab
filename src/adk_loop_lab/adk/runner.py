"""Runner adapter wrapping ADK ``InMemoryRunner`` with lifecycle events."""

from __future__ import annotations

from google.adk import Agent
from google.adk.events import Event as AdkEvent
from google.adk.runners import InMemoryRunner
from google.genai import types

from adk_loop_lab.models import EventType, LoopEvent


def create_runner(
    agent: Agent,
    app_name: str = "adk-loop-lab",
) -> InMemoryRunner:
    """Create an ``InMemoryRunner``.

    Args:
        agent: The root agent to run.
        app_name: Application name for session scoping.

    Returns:
        Configured ``InMemoryRunner``.
    """
    return InMemoryRunner(agent=agent, app_name=app_name)


async def run_agent(
    runner: InMemoryRunner,
    user_id: str,
    session_id: str,
    message: str,
) -> str:
    """Run an agent and collect the final text response.

    Args:
        runner: Configured runner.
        user_id: User identifier.
        session_id: Session identifier.
        message: User message to send.

    Returns:
        The concatenated text emitted by the agent.
    """
    session = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    if session is None:
        await runner.session_service.create_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id,
        )

    final_text_parts: list[str] = []
    new_message = types.Content(role="user", parts=[types.Part(text=message)])

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=new_message,
    ):
        content = event.content
        if not content or not content.parts:
            continue
        if event.partial:
            continue
        for part in content.parts:
            if part.text and not getattr(part, "thought", False):
                final_text_parts.append(part.text)

    return "\n".join(final_text_parts)


def adk_event_to_loop_event(
    adk_event: AdkEvent,
    run_id: str,
    iteration: int,
) -> LoopEvent:
    """Convert an ADK event to the lab's ``LoopEvent`` format.

    Args:
        adk_event: Raw ADK event.
        run_id: Current run identifier.
        iteration: Current iteration number.

    Returns:
        Converted ``LoopEvent``.
    """
    author = getattr(adk_event, "author", "unknown") or "unknown"

    return LoopEvent(
        run_id=run_id,
        iteration=iteration,
        event_type=EventType.MODEL_CALL,
        actor=author,
        payload={
            "adk_event_type": type(adk_event).__name__,
            "invocation_id": getattr(adk_event, "invocation_id", None),
            "partial": getattr(adk_event, "partial", None),
        },
    )
