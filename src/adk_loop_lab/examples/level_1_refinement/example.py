"""Example 1: bounded document refinement loop."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from adk_loop_lab.adk.runner import create_runner, run_agent
from adk_loop_lab.events.recorder import EventRecorder
from adk_loop_lab.examples.level_1_refinement.agents import (
    FAKE_SCRIPT,
    create_critic_agent,
    create_draft_agent,
    create_revision_agent,
    setup_fake_responses,
)
from adk_loop_lab.examples.level_1_refinement.checks import (
    all_checks_pass,
    check_draft,
    count_words,
)
from adk_loop_lab.loop.controller import LoopController
from adk_loop_lab.models import (
    BudgetConfig,
    Decision,
    EvaluationResult,
    EvaluatorStatus,
    LoopRun,
    LoopState,
    Phase,
)
from adk_loop_lab.state.sqlite import SqliteStateStore

CRITIC_THRESHOLD = 0.7


def _attach_fake_callback(*agents: Any) -> None:
    callback = FAKE_SCRIPT.as_callback()
    for agent in agents:
        agent.before_model_callback = callback


def _get_fake_response(prompt: str) -> str:
    for fragment, response in FAKE_SCRIPT._responses:
        if fragment in prompt:
            return response
    raise ValueError(f"No fake response registered for prompt: {prompt}")


def _parse_critique(raw_critique: str) -> dict[str, Any]:
    payload = json.loads(raw_critique)
    score = float(payload["score"])
    passed = bool(payload["pass"]) and score >= CRITIC_THRESHOLD
    feedback = str(payload["feedback"])
    return {"score": score, "pass": passed, "feedback": feedback}


def _build_deterministic_evaluators() -> list[Callable[[LoopState], EvaluationResult]]:
    evaluators: list[Callable[[LoopState], EvaluationResult]] = []

    for evaluator_name in (
        "word_count",
        "concrete_example",
        "generation_vs_verification",
        "unsupported_citations",
    ):

        def evaluate(state: LoopState, name: str = evaluator_name) -> EvaluationResult:
            draft = str(state.facts.get("draft", ""))
            result = next(result for result in check_draft(draft) if result.evaluator_name == name)
            return result

        evaluate.__name__ = f"evaluate_{evaluator_name}"
        evaluators.append(evaluate)

    return evaluators


async def run_example(
    use_fake_model: bool = True,
    *,
    base_dir: str = "var/runs",
    db_path: str = "var/state/level_1_refinement.db",
    model_name: str | None = None,
    max_iterations: int | None = None,
) -> tuple[LoopRun, LoopState]:
    """Run the bounded document refinement example end-to-end."""
    Path(base_dir).mkdir(parents=True, exist_ok=True)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    store = SqliteStateStore(db_path)
    await store.initialize()
    recorder = EventRecorder(base_dir=base_dir)

    run = LoopRun(
        example_id="level_1_refinement",
        goal=(
            "Write a concise explanation of why deterministic verification is "
            "necessary in agentic loops."
        ),
        budgets=BudgetConfig(
            max_iterations=max_iterations or 5,
            max_model_calls=15,
            stagnation_threshold=3,
        ),
    )
    state = LoopState(
        facts={
            "draft": "",
            "draft_history": [],
            "critique_history": [],
            "revision_count": 0,
        }
    )

    draft_agent = create_draft_agent(model=model_name)
    critic_agent = create_critic_agent(model=model_name)
    revision_agent = create_revision_agent(model=model_name)
    draft_runner = None
    critic_runner = None
    revision_runner = None
    if use_fake_model:
        setup_fake_responses()
        _attach_fake_callback(draft_agent, critic_agent, revision_agent)
    else:
        draft_runner = create_runner(draft_agent, app_name="level-1-draft")
        critic_runner = create_runner(critic_agent, app_name="level-1-critic")
        revision_runner = create_runner(revision_agent, app_name="level-1-revision")

    async def run_refinement_agent(
        runner: Any | None,
        session_id: str,
        prompt: str,
    ) -> str:
        if use_fake_model:
            return _get_fake_response(prompt)
        if runner is None:
            raise ValueError("Runner is required when fake mode is disabled.")
        return await run_agent(runner, "user", session_id, prompt)

    async def agent_func(_: str, current_state: LoopState) -> str:
        if current_state.phase is Phase.PLAN:
            current_draft = str(current_state.facts.get("draft", ""))
            if not current_draft:
                draft = await run_refinement_agent(
                    draft_runner,
                    f"{run.run_id}-draft",
                    (
                        "Write a concise explanation (180-260 words) of why deterministic "
                        "verification is necessary in agentic loops. Include a concrete "
                        "example. Distinguish generation from verification."
                    ),
                )
                current_state.facts["draft"] = draft
                current_state.facts["initial_draft"] = draft
                current_state.facts["draft_history"].append(
                    {"revision": 0, "word_count": count_words(draft), "text": draft}
                )
                return draft

            critique_feedback = str(
                current_state.facts.get("critique_feedback", "No critique available.")
            )
            revision_count = int(current_state.facts.get("revision_count", 0)) + 1
            revised_draft = await run_refinement_agent(
                revision_runner,
                f"{run.run_id}-revision",
                (
                    "Revise this explanation based on the critique:\n\n"
                    f"DRAFT:\n{current_draft}\n\n"
                    f"CRITIQUE:\n{critique_feedback}\n\n"
                    "Keep between 180 and 260 words. Include a concrete example. "
                    "Distinguish generation from verification."
                ),
            )
            current_state.facts["draft"] = revised_draft
            current_state.facts["revision_count"] = revision_count
            current_state.facts["draft_history"].append(
                {
                    "revision": revision_count,
                    "word_count": count_words(revised_draft),
                    "text": revised_draft,
                }
            )
            return revised_draft

        if current_state.phase is Phase.REFLECT:
            return str(current_state.facts.get("critique_feedback", ""))

        return ""

    async def evaluate_critic(current_state: LoopState) -> EvaluationResult:
        draft = str(current_state.facts.get("draft", ""))
        if not draft:
            return EvaluationResult(
                evaluator_name="critic_threshold",
                status=EvaluatorStatus.FAIL,
                score=0.0,
                summary="No draft available for critic evaluation.",
                failures=["Draft missing."],
                is_deterministic=False,
            )

        raw_critique = await run_refinement_agent(
            critic_runner,
            f"{run.run_id}-critic-{run.current_iteration}",
            (
                "Evaluate this explanation and return a JSON object with score "
                "(0.0-1.0), pass (boolean), feedback (string):\n\n"
                f"{draft}"
            ),
        )
        critique = _parse_critique(raw_critique)
        current_state.facts["critique_feedback"] = critique["feedback"]
        current_state.facts["critique_score"] = critique["score"]
        current_state.facts["critique_history"].append(
            {
                "iteration": run.current_iteration,
                "score": critique["score"],
                "feedback": critique["feedback"],
            }
        )
        return EvaluationResult(
            evaluator_name="critic_threshold",
            status=EvaluatorStatus.PASS if critique["pass"] else EvaluatorStatus.FAIL,
            score=critique["score"],
            summary=critique["feedback"],
            failures=(
                []
                if critique["pass"]
                else [f"Critic score {critique['score']:.2f} below threshold 0.70."]
            ),
            recommendations=[] if critique["pass"] else [critique["feedback"]],
            is_deterministic=False,
        )

    evaluators: list[Callable[[LoopState], Awaitable[EvaluationResult] | EvaluationResult]] = [
        evaluate_critic,
        *_build_deterministic_evaluators(),
    ]

    controller = LoopController(store, recorder, agent_func=agent_func)
    final_run, final_state = await controller.run(run, state, evaluators=evaluators)

    final_draft = str(final_state.facts.get("draft", ""))
    print("\n" + "=" * 60)
    print("EXAMPLE 1: DOCUMENT REFINEMENT LOOP")
    print("=" * 60)
    print("\nInitial draft:")
    print("-" * 40)
    print(str(final_state.facts.get("initial_draft", "")))
    print("-" * 40)

    for critique in final_state.facts.get("critique_history", []):
        print(
            f"Critique iteration {critique['iteration']}: "
            f"score={critique['score']:.2f} summary={critique['feedback']}"
        )

    for draft_entry in final_state.facts.get("draft_history", [])[1:]:
        print(f"Revision {draft_entry['revision']}: {draft_entry['word_count']} words")

    print(f"\nFinal draft ({count_words(final_draft)} words):")
    print("-" * 40)
    print(final_draft)
    print("-" * 40)

    print("\nDeterministic evaluator scores:")
    for result in check_draft(final_draft):
        print(f"{result.evaluator_name}: {result.score:.2f} ({result.status.value})")
    print(
        f"critic_threshold: {float(final_state.facts.get('critique_score', 0.0)):.2f} "
        f"({'PASS' if float(final_state.facts.get('critique_score', 0.0)) >= CRITIC_THRESHOLD else 'FAIL'})"
    )

    stop_reason = (
        "all criteria satisfied"
        if final_run.last_decision is Decision.SUCCESS
        else (
            "maximum iterations reached"
            if final_run.last_decision is Decision.BUDGET_EXHAUSTED
            else "loop stagnated"
        )
    )
    print(
        f"\nStop decision: {final_run.last_decision.value if final_run.last_decision else 'UNKNOWN'}"
    )
    print(f"Stop reason: {stop_reason}")
    print(f"Iterations: {final_run.current_iteration}")
    print(f"Events recorded: {len(recorder.get_events(final_run.run_id))}")
    print(f"All deterministic checks pass: {all_checks_pass(final_draft)}")

    await store.close()
    return final_run, final_state


if __name__ == "__main__":
    with TemporaryDirectory() as temp_dir:
        asyncio.run(
            run_example(
                use_fake_model=True,
                base_dir=str(Path(temp_dir) / "runs"),
                db_path=str(Path(temp_dir) / "state.db"),
            )
        )
