"""Example 2: Evidence-driven research loop.

Demonstrates a loop that discovers information, identifies evidence gaps,
performs parallel research, and synthesizes results against a local corpus.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from adk_loop_lab.adk.agents import create_agent
from adk_loop_lab.adk.fake_model import FakeModelScript
from adk_loop_lab.adk.runner import create_runner, run_agent
from adk_loop_lab.events.recorder import EventRecorder
from adk_loop_lab.examples.level_2_research.corpus import CorpusStore, Document
from adk_loop_lab.examples.level_2_research.research import (
    ResearchTracker,
    formulate_research_questions,
    generate_report,
)
from adk_loop_lab.loop.controller import LoopController
from adk_loop_lab.models import (
    BudgetConfig,
    EvaluationResult,
    EvaluatorStatus,
    LoopRun,
    LoopState,
    Phase,
)
from adk_loop_lab.state.sqlite import SqliteStateStore


def _attach_fake_callback(agent: Any, script: FakeModelScript) -> None:
    agent.before_model_callback = script.as_callback()


def _get_fake_response(script: FakeModelScript, prompt: str) -> str:
    for fragment, response in script._responses:
        if fragment in prompt:
            return response
    raise ValueError(f"No fake response registered for prompt: {prompt}")


def _build_context(documents: list[Document]) -> str:
    return "\n\n".join(
        f"[{document.doc_id}] {document.title}\n{document.content}" for document in documents
    )


def _parse_claims(response: str) -> list[tuple[str, list[str]]]:
    claims: list[tuple[str, list[str]]] = []
    for line in response.splitlines():
        stripped = line.strip()
        if not stripped.startswith("Claim:"):
            continue

        claim_text = stripped[len("Claim:") :].strip()
        source_match = re.search(r"\[([^\]]+)\]\s*$", stripped)
        doc_ids = [source_match.group(1)] if source_match else []
        if " Source:" in claim_text:
            claim_text = claim_text.split(" Source:", maxsplit=1)[0].strip()
        claims.append((claim_text, doc_ids))
    return claims


def _restore_tracker(state: LoopState) -> ResearchTracker:
    payload = state.facts.get("tracker")
    if isinstance(payload, dict):
        return ResearchTracker.from_dict(payload)
    return ResearchTracker()


def _persist_tracker(state: LoopState, tracker: ResearchTracker) -> None:
    state.facts["tracker"] = tracker.to_dict()
    state.facts["searched_queries"] = sorted(tracker.searched_queries)


def _build_coverage_evaluator() -> Callable[[LoopState], EvaluationResult]:
    def check_coverage(state: LoopState) -> EvaluationResult:
        tracker = _restore_tracker(state)
        gaps = tracker.get_open_gaps()
        answered = sum(1 for question in tracker.questions if question.answered)
        all_answered = answered == len(tracker.questions) and len(tracker.questions) > 0
        has_claims = len(tracker.claims) > 0
        passed = all_answered and has_claims and not gaps
        score = 1.0 if passed else (answered / len(tracker.questions) if tracker.questions else 0.0)
        return EvaluationResult(
            evaluator_name="coverage",
            status=EvaluatorStatus.PASS if passed else EvaluatorStatus.FAIL,
            score=score,
            summary=(
                f"questions_answered={answered}/{len(tracker.questions)} "
                f"claims={len(tracker.claims)} open_gaps={len(gaps)}"
            ),
            failures=[] if passed else [f"Open evidence gaps: {len(gaps)}"],
            evidence_refs=[claim.claim_id for claim in tracker.claims],
            is_deterministic=True,
        )

    return check_coverage


async def run_example(
    use_fake_model: bool = True,
    *,
    base_dir: str = "var/runs",
    db_path: str = "var/state/level_2_research.db",
    model_name: str | None = None,
    max_iterations: int | None = None,
) -> tuple[LoopRun, LoopState]:
    """Run the evidence-driven research example."""
    Path(base_dir).mkdir(parents=True, exist_ok=True)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    store = SqliteStateStore(db_path)
    await store.initialize()
    recorder = EventRecorder(base_dir=base_dir)

    topic = "Compare three approaches to maintaining state in long-running agent workflows."
    run = LoopRun(
        example_id="level_2_research",
        goal=f"Produce an evidence-backed technical report on: {topic}",
        budgets=BudgetConfig(
            max_iterations=max_iterations or 4,
            max_model_calls=20,
            stagnation_threshold=4,
        ),
    )

    corpus_path = Path(__file__).parents[4] / "tests" / "fixtures" / "corpus"
    corpus = CorpusStore(str(corpus_path))
    documents = corpus.load()

    tracker = ResearchTracker()
    questions = formulate_research_questions(topic)
    for question in questions:
        tracker.add_question(question)

    state = LoopState(
        facts={
            "topic": topic,
            "corpus_size": len(documents),
            "questions": questions,
            "report": "",
        }
    )
    _persist_tracker(state, tracker)

    research_agent = create_agent(
        name="researcher",
        instruction=(
            "You are a research assistant. Given a research question and source "
            "documents, extract relevant claims and cite your sources by document ID. "
            "Be precise and avoid unsupported claims."
        ),
        model=model_name,
        output_key="research_notes",
    )

    script = FakeModelScript()
    if use_fake_model:
        script.add(
            "durable state persistence work",
            "Claim: SQLite-backed durable state makes persisted facts authoritative across restarts. Source: corpus summary [state_persistence]",
        )
        script.add(
            "trade-offs of in-memory session state",
            "Claim: In-memory session state offers fast reads but is lost on restart. Source: corpus summary [session_state]",
        )
        script.add(
            "checkpointing systems enable workflow resume",
            "Claim: Checkpointing saves iteration snapshots so a run can resume from a known-good point. Source: corpus summary [checkpointing]",
        )
        script.add(
            "memory systems relate to authoritative workflow state",
            "Claim: Memory systems should complement rather than replace authoritative current state because memory can be stale. Source: corpus summary [memory_systems]",
        )
        _attach_fake_callback(research_agent, script)

    research_runner = None
    if not use_fake_model:
        research_runner = create_runner(research_agent, app_name="level-2-research")

    async def run_research_agent(prompt: str, session_id: str) -> str:
        if use_fake_model:
            return _get_fake_response(script, prompt)
        if research_runner is None:
            raise ValueError("Runner is required when fake mode is disabled.")
        return await run_agent(research_runner, "user", session_id, prompt)

    async def agent_func(_: str, current_state: LoopState) -> str:
        if current_state.phase is not Phase.PLAN:
            return ""

        tracker_state = _restore_tracker(current_state)
        unanswered = [question for question in tracker_state.questions if not question.answered]
        if not unanswered:
            report = generate_report(
                topic, tracker_state, [document.doc_id for document in documents]
            )
            current_state.facts["report"] = report
            _persist_tracker(current_state, tracker_state)
            return "all_answered"

        question = unanswered[0]
        if tracker_state.deduplicate_query(question.text):
            question.answered = True
            _persist_tracker(current_state, tracker_state)
            return "duplicate_query_skipped"

        relevant_documents = corpus.search(question.text, limit=3)
        question.relevant_docs = [document.doc_id for document in relevant_documents]
        current_state.facts["current_question"] = question.text
        current_state.facts["current_sources"] = list(question.relevant_docs)

        prompt = (
            f"Research question: {question.text}\n\n"
            f"Source documents:\n{_build_context(relevant_documents)}\n\n"
            "Extract claims with source citations in format:\n"
            "Claim: <text> Source: <description> [doc_id]"
        )
        response = await run_research_agent(
            prompt,
            f"{run.run_id}-{question.question_id}",
        )

        for claim_text, doc_ids in _parse_claims(response):
            tracker_state.add_claim(claim_text, doc_ids)

        question.answered = True
        _persist_tracker(current_state, tracker_state)

        if all(item.answered for item in tracker_state.questions):
            current_state.facts["report"] = generate_report(
                topic,
                tracker_state,
                [document.doc_id for document in documents],
            )

        return response

    controller = LoopController(store, recorder, agent_func=agent_func)
    final_run, final_state = await controller.run(
        run,
        state,
        evaluators=[_build_coverage_evaluator()],
    )

    final_tracker = _restore_tracker(final_state)
    report = str(final_state.facts.get("report", ""))
    if not report:
        report = generate_report(topic, final_tracker, [document.doc_id for document in documents])
        final_state.facts["report"] = report

    print("\n" + "=" * 60)
    print("EXAMPLE 2: EVIDENCE-DRIVEN RESEARCH LOOP")
    print("=" * 60)
    print(f"\n{report}")
    print(f"\nStop decision: {final_run.last_decision}")
    print(f"Iterations: {final_run.current_iteration}")
    print(f"Claims: {len(final_tracker.claims)}")

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
