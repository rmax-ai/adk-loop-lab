"""Deterministic checks for document refinement."""

from adk_loop_lab.evaluation.composite import evaluate_composite
from adk_loop_lab.evaluation.deterministic import not_contains_validator, range_validator
from adk_loop_lab.models import CompositePolicy, EvaluationResult, EvaluatorStatus


def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def check_draft(text: str) -> list[EvaluationResult]:
    """Run all deterministic checks on a draft."""
    normalized = text.lower()
    results: list[EvaluationResult] = []

    word_count = count_words(text)
    results.append(range_validator(word_count, 180, 260, "word_count"))

    has_example = any(
        phrase in normalized for phrase in ("example", "consider", "for instance", "imagine")
    )
    results.append(
        EvaluationResult(
            evaluator_name="concrete_example",
            status=EvaluatorStatus.PASS if has_example else EvaluatorStatus.FAIL,
            score=1.0 if has_example else 0.0,
            summary=(
                "Contains a concrete example."
                if has_example
                else "Missing a concrete example signal."
            ),
            failures=[] if has_example else ["No example phrase detected."],
            is_deterministic=True,
        )
    )

    distinguishes = (
        "generation" in normalized
        and "verification" in normalized
        and any(term in normalized for term in ("confirm", "check", "validate", "propose"))
    )
    results.append(
        EvaluationResult(
            evaluator_name="generation_vs_verification",
            status=EvaluatorStatus.PASS if distinguishes else EvaluatorStatus.FAIL,
            score=1.0 if distinguishes else 0.0,
            summary=(
                "Explains the separation between generation and verification."
                if distinguishes
                else "Does not clearly separate generation from verification."
            ),
            failures=[] if distinguishes else ["Missing generation-versus-verification contrast."],
            is_deterministic=True,
        )
    )

    results.append(
        not_contains_validator(
            normalized,
            ["according to", "studies show", "research indicates", "experts agree"],
            "unsupported_citations",
        )
    )
    return results


def all_checks_pass(text: str) -> bool:
    """Check whether all deterministic validators pass."""
    composite = evaluate_composite(check_draft(text), CompositePolicy.DETERMINISTIC_VETO)
    return composite.overall_status is EvaluatorStatus.PASS
