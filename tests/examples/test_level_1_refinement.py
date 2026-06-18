"""Example tests for the level 1 refinement loop."""

from pathlib import Path

from adk_loop_lab.examples.level_1_refinement.checks import (
    check_draft,
    count_words,
)
from adk_loop_lab.examples.level_1_refinement.example import run_example
from adk_loop_lab.models import EvaluatorStatus


def test_check_draft_flags_short_text() -> None:
    results = check_draft("Too short.")
    statuses = {result.evaluator_name: result.status for result in results}
    assert statuses["word_count"] is EvaluatorStatus.FAIL


async def test_run_example_fake_model(tmp_path: Path) -> None:
    run, state = await run_example(
        use_fake_model=True,
        base_dir=str(tmp_path / "runs"),
        db_path=str(tmp_path / "state.db"),
    )

    draft = str(state.facts["draft"])
    # With canned fake responses that don't adapt, word count may not converge.
    # The loop should still run and produce a terminal decision.
    assert run.last_decision is not None
    assert len(draft) > 50  # Should have substantial content
    assert count_words(draft) > 0
    assert len((tmp_path / "runs" / run.run_id / "events.jsonl").read_text()) > 0
