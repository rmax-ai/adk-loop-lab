"""Workflow construction helpers for ADK graph-based execution."""

from __future__ import annotations

from google.adk import Agent, Workflow
from google.adk.agents.context import Context
from google.adk.workflow import DEFAULT_ROUTE, node


def sequential_workflow(
    name: str,
    agents: list[Agent],
) -> Workflow:
    """Create a sequential workflow.

    Args:
        name: Workflow name.
        agents: Ordered list of agents to run sequentially.

    Returns:
        Workflow with linear edges.

    Raises:
        ValueError: If ``agents`` is empty.
    """
    if not agents:
        raise ValueError("sequential_workflow requires at least one agent")

    return Workflow(name=name, edges=[("START", *agents)])


def parallel_workflow(
    name: str,
    agents: list[Agent],
) -> Workflow:
    """Create a parallel fan-out workflow.

    Args:
        name: Workflow name.
        agents: Agents to run in parallel from START.

    Returns:
        Workflow with fan-out edges.

    Raises:
        ValueError: If ``agents`` is empty.
    """
    if not agents:
        raise ValueError("parallel_workflow requires at least one agent")

    return Workflow(name=name, edges=[("START", tuple(agents))])


def generator_critic_workflow(
    name: str,
    generator: Agent,
    critic: Agent,
    max_rounds: int = 5,
) -> Workflow:
    """Create a generator-critic loop workflow.

    Args:
        name: Workflow name.
        generator: Agent that generates content.
        critic: Agent that evaluates and provides feedback.
        max_rounds: Maximum refinement rounds.

    Returns:
        Workflow with a routed generator-critic loop.

    Raises:
        ValueError: If ``max_rounds`` is below 1.
    """
    if max_rounds < 1:
        raise ValueError("max_rounds must be at least 1")

    round_state_key = f"{name}_generator_critic_round"

    @node(name=f"{name}_critic_router")
    def critic_router(ctx: Context, node_input: str) -> str:
        """Route generator retries based on critic output and round budget."""
        rounds = int(ctx.state.get(round_state_key, 0)) + 1
        ctx.state[round_state_key] = rounds

        normalized = node_input.casefold()
        approved_markers = (
            '"pass": true',
            '"pass":true',
            "pass: true",
            "approved",
            "looks good",
        )
        should_stop = rounds >= max_rounds or any(
            marker in normalized for marker in approved_markers
        )
        ctx.route = "stop" if should_stop else "retry"
        return node_input

    return Workflow(
        name=name,
        edges=[
            ("START", generator, critic, critic_router),
            (critic_router, {"retry": generator, DEFAULT_ROUTE: critic_router}),
        ],
    )
