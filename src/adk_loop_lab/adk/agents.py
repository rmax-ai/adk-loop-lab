"""Agent factory for creating ADK agents with standardized configuration."""

from __future__ import annotations

from typing import Any

from google.adk import Agent
from google.adk.agents.llm_agent import LlmAgent

from adk_loop_lab.adk.compatibility import get_default_model


def create_agent(
    name: str,
    instruction: str,
    *,
    model: str | None = None,
    tools: list[Any] | None = None,
    output_key: str | None = None,
    output_schema: Any = None,
) -> LlmAgent:
    """Create a standard ``LlmAgent`` with sensible defaults.

    Args:
        name: Unique agent name.
        instruction: System instruction for the agent.
        model: Model name. Defaults to ``gemini-3-flash-preview``.
        tools: List of tools or tool callables.
        output_key: Session state key for auto-saving final response.
        output_schema: Structured output schema for the final response.

    Returns:
        Configured ``LlmAgent`` instance.
    """
    return Agent(
        name=name,
        model=model or get_default_model(),
        instruction=instruction,
        tools=tools or [],
        output_key=output_key,
        output_schema=output_schema,
    )
