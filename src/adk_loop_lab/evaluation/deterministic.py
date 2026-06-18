"""Deterministic evaluators — rule-based checks.

These run first and their failures veto success regardless of model judge scores.
"""

from typing import Any

from adk_loop_lab.models import EvaluationResult, EvaluatorStatus


def schema_validator(data: dict[str, Any], schema: dict[str, type[Any]]) -> EvaluationResult:
    """Validate data against a simple schema."""
    failures: list[str] = []
    for key, expected_type in schema.items():
        if key not in data:
            failures.append(f"Missing required key: {key}")
            continue
        if not isinstance(data[key], expected_type):
            failures.append(
                f"Key '{key}' expected type {expected_type.__name__}, got {type(data[key]).__name__}"
            )

    return _build_result(
        evaluator_name="schema_validator",
        failures=failures,
        pass_summary="Schema validation passed.",
        fail_summary="Schema validation failed.",
    )


def exact_match_validator(actual: str, expected: str) -> EvaluationResult:
    """Check if actual string contains the expected substring."""
    failures: list[str] = []
    if expected not in actual:
        failures.append(f"Expected substring not found: {expected}")

    return _build_result(
        evaluator_name="exact_match_validator",
        failures=failures,
        pass_summary="Expected substring found.",
        fail_summary="Expected substring missing.",
    )


def range_validator(
    value: float,
    min_val: float,
    max_val: float,
    label: str = "",
) -> EvaluationResult:
    """Check if value is within [min_val, max_val]."""
    failures: list[str] = []
    evaluator_name = label or "range_validator"

    if value < min_val or value > max_val:
        failures.append(f"{evaluator_name} out of range: {value} not in [{min_val}, {max_val}]")

    return _build_result(
        evaluator_name=evaluator_name,
        failures=failures,
        pass_summary=f"{evaluator_name} within range.",
        fail_summary=f"{evaluator_name} outside allowed range.",
    )


def list_contains_validator(
    items: list[Any], required: list[Any], label: str = ""
) -> EvaluationResult:
    """Check if all required items are present in the list."""
    evaluator_name = label or "list_contains_validator"
    failures = [f"Missing required item: {item}" for item in required if item not in items]

    return _build_result(
        evaluator_name=evaluator_name,
        failures=failures,
        pass_summary=f"{evaluator_name} contains all required items.",
        fail_summary=f"{evaluator_name} is missing required items.",
    )


def not_contains_validator(text: str, forbidden: list[str], label: str = "") -> EvaluationResult:
    """Check that text does NOT contain any forbidden patterns."""
    evaluator_name = label or "not_contains_validator"
    failures = [f"Forbidden pattern found: {pattern}" for pattern in forbidden if pattern in text]

    return _build_result(
        evaluator_name=evaluator_name,
        failures=failures,
        pass_summary=f"{evaluator_name} contains no forbidden patterns.",
        fail_summary=f"{evaluator_name} contains forbidden patterns.",
    )


def _build_result(
    *,
    evaluator_name: str,
    failures: list[str],
    pass_summary: str,
    fail_summary: str,
) -> EvaluationResult:
    status = EvaluatorStatus.FAIL if failures else EvaluatorStatus.PASS
    return EvaluationResult(
        evaluator_name=evaluator_name,
        status=status,
        score=0.0 if failures else 1.0,
        summary=fail_summary if failures else pass_summary,
        failures=failures,
        is_deterministic=True,
    )
