"""Agents for the document refinement example."""

from google.adk import Agent

from adk_loop_lab.adk.agents import create_agent
from adk_loop_lab.adk.fake_model import FakeModelScript

FAKE_SCRIPT = FakeModelScript()


def setup_fake_responses() -> None:
    """Register canned responses for deterministic testing."""
    FAKE_SCRIPT._responses.clear()
    FAKE_SCRIPT.add(
        "Write a concise explanation (180-260 words)",
        (
            "Deterministic verification matters in agentic loops because it separates "
            "what a model suggests from what the system can safely accept. A model can "
            "sound confident while still being wrong. Consider a coding agent that says "
            "a patch fixed a bug because the diff looks reasonable. If the loop accepts "
            "that claim without running tests, checking exit codes, or validating output "
            "schemas, it starts building future decisions on an invented success. "
            "Generation is the step where the model produces a candidate answer, plan, "
            "or patch. Verification is the step where the control plane checks that "
            "candidate against rules that do not depend on the model's self-belief. "
            "Without that boundary, the agent becomes both author and judge."
        ),
    )
    FAKE_SCRIPT.add(
        "Evaluate this explanation and return a JSON object",
        (
            '{"score": 0.84, "pass": true, "feedback": "Clear distinction between '
            "generation and verification with a concrete coding example. Expand the "
            "explanation so the operational role of deterministic checks is more "
            'explicit."}'
        ),
    )
    FAKE_SCRIPT.add(
        "Revise this explanation based on the critique",
        (
            "Deterministic verification is necessary in agentic loops because it creates "
            "an independent gate between generation and acceptance. A model can produce "
            "a fluent answer, a plausible plan, or a confident claim, but that does not "
            "make the result true. Consider a coding agent that generates a patch and "
            "says the bug is fixed. The generation step proposes the patch and explains "
            "why it should work. The verification step runs the test suite, checks exit "
            "codes, validates file changes, and confirms the observed behavior matches "
            "the goal. Those checks are deterministic because the same inputs should "
            "produce the same verdict every time. That separation matters because it "
            "prevents the model from acting as both author and judge of its own work. "
            "When generation and verification are collapsed together, loops can drift on "
            "top of plausible mistakes. When they stay separate, each iteration builds "
            "on confirmed facts instead of hopeful narration."
        ),
    )


def create_draft_agent(*, model: str | None = None) -> Agent:
    """Create the draft-writing agent."""
    return create_agent(
        name="draft_agent",
        instruction=(
            "You are a technical writer. Write a concise explanation of why "
            "deterministic verification is necessary in agentic loops. Include a "
            "concrete example. Distinguish generation from verification. Be precise "
            "and avoid unsupported claims."
        ),
        model=model,
        output_key="draft",
    )


def create_critic_agent(*, model: str | None = None) -> Agent:
    """Create the critic agent that evaluates drafts."""
    return create_agent(
        name="critic_agent",
        instruction=(
            "You are a strict editor. Evaluate the provided explanation for clarity, "
            "correctness, and completeness. Return a JSON object with score "
            "(0.0-1.0), pass (boolean), and feedback (string)."
        ),
        model=model,
        output_key="critique",
    )


def create_revision_agent(*, model: str | None = None) -> Agent:
    """Create the revision agent that improves drafts."""
    return create_agent(
        name="revision_agent",
        instruction=(
            "You are a technical writer improving an explanation. Revise the draft "
            "based on the critique provided. Keep it between 180 and 260 words, "
            "include a concrete example, and distinguish generation from verification."
        ),
        model=model,
        output_key="draft",
    )
