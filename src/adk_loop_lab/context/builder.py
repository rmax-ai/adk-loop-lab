"""Context builder for loop iterations.

Constructs model prompts by selecting relevant information:
goal + acceptance criteria + active constraints + current state +
authoritative observations + verified memories + recent failures + budget status.

Excludes: complete event history, all previous model responses, irrelevant output.
"""

from typing import Any

from adk_loop_lab.models import LoopRun, LoopState


class ContextBuilder:
    """Builds context prompts for model invocations during loop execution."""

    def __init__(self, max_memory_items: int = 5, max_failure_items: int = 3) -> None:
        """Initialize the builder with bounded context section sizes."""
        self._max_memory_items = max_memory_items
        self._max_failure_items = max_failure_items

    def build_plan_context(self, run: LoopRun, state: LoopState) -> str:
        """Build context for the PLAN phase."""
        sections: list[tuple[str, list[str]]] = []
        included_sections: dict[str, int] = {}

        sections.append(("Goal", [run.goal]))
        included_sections["goal"] = 1

        criteria_lines = self._format_acceptance_criteria(run)
        sections.append(("Acceptance Criteria", criteria_lines))
        included_sections["acceptance_criteria"] = len(criteria_lines)

        constraint_lines = state.constraints or ["None recorded."]
        sections.append(("Constraints", constraint_lines))
        included_sections["constraints"] = len(state.constraints)

        state_lines = [
            f"Phase: {state.phase.value}",
            f"Progress Score: {state.progress_score:.2f}",
            f"Stagnation Count: {state.stagnation_count}",
            f"Current Iteration: {run.current_iteration}/{run.max_iterations}",
        ]
        sections.append(("Current State", state_lines))
        included_sections["current_state"] = len(state_lines)

        pending_actions = state.pending_actions or ["None pending."]
        sections.append(("Pending Actions", pending_actions))
        included_sections["pending_actions"] = len(state.pending_actions)

        observation_lines, observation_count = self._collect_observations(state)
        sections.append(("Authoritative Observations", observation_lines))
        included_sections["authoritative_observations"] = observation_count

        memory_lines, memory_count = self._collect_verified_memories(state)
        sections.append(("Verified Memories", memory_lines))
        included_sections["verified_memories"] = memory_count

        failure_lines = self._format_recent_failures(state)
        sections.append(("Recent Failures", failure_lines))
        included_sections["recent_failures"] = min(
            len(state.failed_attempts), self._max_failure_items
        )

        budget_lines = self._format_budget_status(run, state)
        sections.append(("Budget", budget_lines))
        included_sections["budget"] = len(budget_lines)

        manifest = self.build_context_manifest(included_sections)
        sections.append(
            (
                "Context Manifest",
                [
                    f"Included Sections: {manifest['included_sections']}",
                    f"Excluded Counts: {manifest['excluded_counts']}",
                    f"Estimated Tokens: {manifest['estimated_tokens']}",
                ],
            )
        )
        return self._render_sections(sections)

    def build_reflect_context(self, run: LoopRun, state: LoopState) -> str:
        """Build context for the REFLECT phase."""
        sections: list[tuple[str, list[str]]] = []
        included_sections: dict[str, int] = {}

        sections.append(("Goal", [run.goal]))
        included_sections["goal"] = 1

        criteria_lines = self._format_acceptance_criteria(run)
        sections.append(("Acceptance Criteria", criteria_lines))
        included_sections["acceptance_criteria"] = len(criteria_lines)

        completed_actions = state.completed_actions[-self._max_memory_items :] or [
            "None completed."
        ]
        sections.append(("Completed Actions", completed_actions))
        included_sections["completed_actions"] = min(
            len(state.completed_actions), self._max_memory_items
        )

        failure_lines = self._format_recent_failures(state)
        sections.append(("Failed Attempts", failure_lines))
        included_sections["failed_attempts"] = min(
            len(state.failed_attempts), self._max_failure_items
        )

        evaluation_lines, evaluation_count = self._collect_evaluations(state)
        sections.append(("Evaluation Results", evaluation_lines))
        included_sections["evaluation_results"] = evaluation_count

        lesson_lines, lesson_count = self._collect_verified_memories(state)
        sections.append(("Verified Lessons", lesson_lines))
        included_sections["verified_lessons"] = lesson_count

        state_lines = [
            f"Phase: {state.phase.value}",
            f"Progress Score: {state.progress_score:.2f}",
            f"Stagnation Count: {state.stagnation_count}",
            f"Evaluation History Entries: {len(state.evaluation_history)}",
        ]
        sections.append(("Current State", state_lines))
        included_sections["current_state"] = len(state_lines)

        manifest = self.build_context_manifest(included_sections)
        sections.append(
            (
                "Context Manifest",
                [
                    f"Included Sections: {manifest['included_sections']}",
                    f"Excluded Counts: {manifest['excluded_counts']}",
                    f"Estimated Tokens: {manifest['estimated_tokens']}",
                ],
            )
        )
        return self._render_sections(sections)

    def build_context_manifest(self, sections: dict[str, int]) -> dict[str, Any]:
        """Produce a context manifest showing what was included/excluded."""
        excluded_counts = {
            "omitted_memories": max(
                0, sections.get("verified_memories", 0) - self._max_memory_items
            ),
            "omitted_failures": max(
                0, sections.get("recent_failures", 0) - self._max_failure_items
            ),
            "event_history_entries": "excluded",
            "model_responses": "excluded",
        }
        estimated_tokens = max(
            1,
            sum(max(1, value) for value in sections.values()) * 12,
        )
        return {
            "included_sections": dict(sections),
            "excluded_counts": excluded_counts,
            "estimated_tokens": estimated_tokens,
        }

    def _collect_evaluations(self, state: LoopState) -> tuple[list[str], int]:
        evaluation_ids = state.evaluation_history[-self._max_memory_items :]
        if not evaluation_ids:
            return ["No evaluation history recorded."], 0
        return [f"Evaluation ID: {evaluation_id}" for evaluation_id in evaluation_ids], len(
            evaluation_ids
        )

    def _collect_observations(self, state: LoopState) -> tuple[list[str], int]:
        observation_values = state.facts.get("authoritative_observations")
        if isinstance(observation_values, list):
            observations = [str(item) for item in observation_values[: self._max_memory_items]]
            if observations:
                return observations, len(observations)

        fact_lines = [
            f"{key}: {self._stringify_value(value)}"
            for key, value in sorted(state.facts.items())
            if key not in {"verified_memories", "lessons_learned", "authoritative_observations"}
        ]
        if not fact_lines:
            return ["No authoritative observations recorded."], 0
        return fact_lines[: self._max_memory_items], min(len(fact_lines), self._max_memory_items)

    def _collect_verified_memories(self, state: LoopState) -> tuple[list[str], int]:
        memory_candidates = state.facts.get("verified_memories")
        if not isinstance(memory_candidates, list):
            memory_candidates = state.facts.get("lessons_learned", [])

        if not isinstance(memory_candidates, list) or not memory_candidates:
            return ["No verified memories recorded."], 0

        memory_lines = [
            self._stringify_value(item) for item in memory_candidates[: self._max_memory_items]
        ]
        return memory_lines, len(memory_lines)

    def _format_acceptance_criteria(self, run: LoopRun) -> list[str]:
        if not run.acceptance_criteria:
            return ["None recorded."]

        return [
            f"- [{'x' if criterion.met else ' '}] {criterion.key}: {criterion.description}"
            for criterion in run.acceptance_criteria
        ]

    def _format_budget_status(self, run: LoopRun, state: LoopState) -> list[str]:
        budget_state = state.facts.get("budget_state")
        model_calls = getattr(budget_state, "model_calls", None)
        tool_calls = getattr(budget_state, "tool_calls", None)

        if isinstance(budget_state, dict):
            model_calls = budget_state.get("model_calls")
            tool_calls = budget_state.get("tool_calls")

        if model_calls is None:
            model_calls = 0
        if tool_calls is None:
            tool_calls = 0

        return [
            (
                f"{run.current_iteration}/{run.budgets.max_iterations} iterations, "
                f"{model_calls}/{run.budgets.max_model_calls} model calls, "
                f"{tool_calls}/{run.budgets.max_tool_calls} tool calls"
            )
        ]

    def _format_recent_failures(self, state: LoopState) -> list[str]:
        failures = state.failed_attempts[-self._max_failure_items :]
        if not failures:
            return ["None recorded."]
        return failures

    def _render_sections(self, sections: list[tuple[str, list[str]]]) -> str:
        rendered_sections: list[str] = []
        for title, lines in sections:
            body = "\n".join(lines)
            rendered_sections.append(f"## {title}\n{body}")
        return "\n\n".join(rendered_sections).strip()

    def _stringify_value(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float, bool)) or value is None:
            return str(value)
        if isinstance(value, list):
            return ", ".join(self._stringify_value(item) for item in value)
        if isinstance(value, dict):
            return ", ".join(
                f"{key}={self._stringify_value(nested_value)}"
                for key, nested_value in sorted(value.items())
            )
        return str(value)
