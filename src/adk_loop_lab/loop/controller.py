"""Main loop controller.

Orchestrates the full agentic loop lifecycle:
DISCOVER -> PLAN -> EXECUTE -> VERIFY -> COMMIT -> REFLECT -> DECIDE

The controller is deterministic. Models are invoked via ADK agents only
at PLAN and REFLECT phases (through the agent_factory callback).
"""

import inspect
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from adk_loop_lab.events.console import (
    format_decision,
    format_evaluation_line,
    format_iteration_header,
)
from adk_loop_lab.events.recorder import EventRecorder
from adk_loop_lab.loop.checkpoints import CheckpointManager
from adk_loop_lab.loop.lifecycle import is_terminal, next_phase
from adk_loop_lab.loop.policies import BudgetManager, StoppingPolicy
from adk_loop_lab.loop.recovery import FailureType, RecoveryPolicy
from adk_loop_lab.models import (
    Decision,
    EvaluationResult,
    EvaluatorStatus,
    EventType,
    LoopEvent,
    LoopRun,
    LoopState,
    Phase,
    RunStatus,
)
from adk_loop_lab.state.sqlite import SqliteStateStore
from adk_loop_lab.state.transactions import TransactionManager

logger = logging.getLogger(__name__)


AgentFunc = Callable[[str, LoopState], Awaitable[str]]
EvaluatorFunc = Callable[[LoopState], Any]
ToolFunc = Callable[..., Any]


class LoopController:
    """Main loop controller - deterministic lifecycle orchestrator."""

    def __init__(
        self,
        store: SqliteStateStore,
        recorder: EventRecorder,
        agent_func: AgentFunc | None = None,
    ) -> None:
        """Initialize the controller."""
        self._store = store
        self._recorder = recorder
        self._agent_func = agent_func
        self._checkpoints = CheckpointManager(store, recorder)
        self._recovery = RecoveryPolicy()
        self._budget: BudgetManager | None = None
        self._stopping: StoppingPolicy | None = None
        self._tools: dict[str, ToolFunc] = {}
        self._evaluators: list[EvaluatorFunc] = []
        self._current_events: list[LoopEvent] = []
        self._previous_progress_score = 0.0
        self._all_criteria_met = False

    async def run(
        self,
        run: LoopRun,
        state: LoopState,
        *,
        evaluators: list[EvaluatorFunc] | None = None,
        tools: dict[str, ToolFunc] | None = None,
    ) -> tuple[LoopRun, LoopState]:
        """Run the full loop lifecycle until a terminal decision."""
        return await self._run_loop(
            run,
            state,
            evaluators=evaluators,
            tools=tools,
            emit_run_started=True,
        )

    async def _run_loop(
        self,
        run: LoopRun,
        state: LoopState,
        *,
        evaluators: list[EvaluatorFunc] | None,
        tools: dict[str, ToolFunc] | None,
        emit_run_started: bool,
    ) -> tuple[LoopRun, LoopState]:
        """Run the lifecycle using the current run state as the starting point."""
        self._budget = BudgetManager(run.budgets)
        self._stopping = StoppingPolicy(run.budgets)
        self._recovery = RecoveryPolicy(
            max_attempts=run.budgets.retry_max_attempts,
            backoff_seconds=run.budgets.retry_backoff_seconds,
        )
        self._tools = tools or {}
        self._evaluators = evaluators or []
        self._current_events = []
        self._previous_progress_score = state.progress_score
        self._all_criteria_met = False

        run.max_iterations = run.budgets.max_iterations
        run.status = RunStatus.RUNNING
        state.phase = Phase.DISCOVER
        self._budget.state.iteration = run.current_iteration

        await self._store.save_run(run)
        await self._store.save_state(run.run_id, state)
        if emit_run_started:
            self._record_event(
                run.run_id,
                run.current_iteration,
                EventType.RUN_STARTED,
                payload={"goal": run.goal, "example_id": run.example_id},
            )

        try:
            while True:
                run.current_iteration += 1
                self._budget.state.iteration = run.current_iteration
                state.phase = Phase.DISCOVER
                self._current_events = []

                print(format_iteration_header(run, state, self._budget.state))
                self._record_event(
                    run.run_id,
                    run.current_iteration,
                    EventType.ITERATION_STARTED,
                    payload={"iteration": run.current_iteration},
                )

                await self._run_phase(run, state, Phase.DISCOVER, self._discover)
                await self._run_phase(run, state, Phase.PLAN, self._plan)
                await self._run_phase(run, state, Phase.EXECUTE, self._execute)
                await self._run_phase(run, state, Phase.VERIFY, self._verify)
                await self._run_phase(run, state, Phase.COMMIT, self._commit)
                await self._run_phase(run, state, Phase.REFLECT, self._reflect, buffer=False)
                decision = await self._run_decide_phase(run, state)

                run.last_decision = decision
                self._record_event(
                    run.run_id,
                    run.current_iteration,
                    EventType.STOP_DECISION,
                    payload={"decision": decision.value},
                )
                print(format_decision(decision))

                if decision is Decision.STAGNATED:
                    self._record_event(
                        run.run_id,
                        run.current_iteration,
                        EventType.PROGRESS_STAGNATED,
                        payload={"stagnation_count": state.stagnation_count},
                    )

                self._record_event(
                    run.run_id,
                    run.current_iteration,
                    EventType.ITERATION_COMPLETED,
                    payload={"decision": decision.value},
                )

                if is_terminal(decision):
                    run.status = (
                        RunStatus.COMPLETED if decision is Decision.SUCCESS else RunStatus.FAILED
                    )
                    break

                state.phase = next_phase(Phase.DECIDE)

            await self._store.save_run(run)
            await self._store.save_state(run.run_id, state)
            self._record_event(
                run.run_id,
                run.current_iteration,
                EventType.RUN_COMPLETED,
                payload={"status": run.status.value, "decision": run.last_decision.value},
            )
            return run, state
        except Exception as error:
            logger.exception("loop_controller_failed", extra={"run_id": run.run_id})
            run.status = RunStatus.FAILED
            run.last_decision = Decision.FAILED
            await self._store.save_run(run)
            await self._store.save_state(run.run_id, state)
            self._record_event(
                run.run_id,
                run.current_iteration,
                EventType.ERROR,
                payload={"message": str(error), "phase": state.phase.value},
            )
            self._record_event(
                run.run_id,
                run.current_iteration,
                EventType.RUN_FAILED,
                payload={"message": str(error)},
            )
            return run, state

    async def _discover(self, run: LoopRun, state: LoopState) -> None:
        """DISCOVER phase: inspect current world and task state."""
        state.facts["last_goal"] = run.goal
        state.facts["current_iteration"] = run.current_iteration
        self._buffer_event(
            run.run_id,
            run.current_iteration,
            EventType.STATE_CHANGE,
            payload={"observation_keys": sorted(state.facts.keys())},
        )

    async def _plan(self, run: LoopRun, state: LoopState) -> None:
        """PLAN phase: propose next bounded action via model."""
        if self._agent_func is None:
            return

        prompt = (
            "plan next action\n"
            f"goal: {run.goal}\n"
            f"iteration: {run.current_iteration}\n"
            f"pending_actions: {state.pending_actions}\n"
            f"completed_actions: {state.completed_actions}"
        )
        self._buffer_event(
            run.run_id,
            run.current_iteration,
            EventType.MODEL_CALL,
            payload={"phase": Phase.PLAN.value, "prompt": prompt},
        )
        plan_text = await self._recovery.with_recovery(
            "plan_next_action",
            self._agent_func,
            prompt,
            state,
            failure_type=FailureType.MALFORMED_OUTPUT,
        )
        self._require_budget().record_model_call()
        state.facts["last_plan"] = plan_text
        run.active_plan = plan_text
        if plan_text and plan_text not in state.pending_actions:
            state.pending_actions.append(plan_text)
        self._buffer_event(
            run.run_id,
            run.current_iteration,
            EventType.MODEL_RESPONSE,
            payload={"phase": Phase.PLAN.value, "response": plan_text},
        )
        self._buffer_event(
            run.run_id,
            run.current_iteration,
            EventType.BUDGET_UPDATE,
            payload=self._require_budget().state.model_dump(mode="json"),
        )

    async def _execute(self, run: LoopRun, state: LoopState) -> None:
        """EXECUTE phase: perform approved action."""
        if not self._tools or not state.pending_actions:
            return

        action_name = state.pending_actions[0]
        tool = self._tools.get(action_name)
        if tool is None:
            state.failed_attempts.append(action_name)
            return

        tool_args = self._resolve_tool_args(state, action_name)
        self._buffer_event(
            run.run_id,
            run.current_iteration,
            EventType.TOOL_CALL,
            payload={"tool_name": action_name, "tool_args": tool_args},
        )
        result = await self._recovery.with_recovery(
            f"execute_tool:{action_name}",
            self._invoke_tool,
            tool,
            tool_args,
            failure_type=FailureType.TOOL_FAILURE,
        )
        self._require_budget().record_tool_call()
        state.pending_actions.pop(0)
        state.completed_actions.append(action_name)
        state.facts["last_tool_result"] = result
        self._buffer_event(
            run.run_id,
            run.current_iteration,
            EventType.TOOL_RESULT,
            payload={"tool_name": action_name, "result": self._coerce_payload_value(result)},
        )
        self._buffer_event(
            run.run_id,
            run.current_iteration,
            EventType.BUDGET_UPDATE,
            payload=self._require_budget().state.model_dump(mode="json"),
        )

    async def _verify(self, run: LoopRun, state: LoopState) -> None:
        """VERIFY phase: evaluate results."""
        results: list[EvaluationResult] = []
        for evaluator in self._evaluators:
            result = await self._recovery.with_recovery(
                f"evaluate:{getattr(evaluator, '__name__', evaluator.__class__.__name__)}",
                self._invoke_evaluator,
                evaluator,
                state,
                failure_type=FailureType.EVALUATOR_ERROR,
            )
            results.append(self._normalize_evaluation_result(evaluator, result))

        if results:
            state.progress_score = sum(result.score for result in results) / len(results)
            for result in results:
                state.evaluation_history.append(result.evaluation_id)
                self._buffer_event(
                    run.run_id,
                    run.current_iteration,
                    EventType.EVALUATION_RESULT,
                    payload=result.model_dump(mode="json"),
                )
                print(format_evaluation_line(result))
            all_passed = all(result.status is EvaluatorStatus.PASS for result in results)
            self._all_criteria_met = all_passed
            self._buffer_event(
                run.run_id,
                run.current_iteration,
                EventType.VERIFICATION_PASSED if all_passed else EventType.VERIFICATION_FAILED,
                payload={"score": state.progress_score},
            )
        else:
            self._all_criteria_met = all(
                criterion.met for criterion in run.acceptance_criteria
            ) and bool(run.acceptance_criteria)

        if state.progress_score > self._previous_progress_score:
            state.stagnation_count = 0
        else:
            state.stagnation_count += 1
        self._previous_progress_score = state.progress_score

    async def _commit(self, run: LoopRun, state: LoopState) -> None:
        """COMMIT phase: atomically persist state."""
        manager = TransactionManager(self._store, run.run_id)
        await self._recovery.with_recovery(
            "commit_iteration",
            manager.commit_iteration,
            run,
            state,
            list(self._current_events),
            self._recorder,
            failure_type=FailureType.STATE_STORE_FAILURE,
        )
        self._current_events.clear()
        await self._recovery.with_recovery(
            "create_checkpoint",
            self._checkpoints.create_checkpoint,
            run,
            state,
            failure_type=FailureType.STATE_STORE_FAILURE,
        )

    async def _reflect(self, run: LoopRun, state: LoopState) -> None:
        """REFLECT phase: extract lessons."""
        if self._agent_func is None:
            return

        prompt = (
            "reflect on results\n"
            f"goal: {run.goal}\n"
            f"progress_score: {state.progress_score}\n"
            f"completed_actions: {state.completed_actions[-3:]}\n"
            f"failed_attempts: {state.failed_attempts[-3:]}"
        )
        self._record_event(
            run.run_id,
            run.current_iteration,
            EventType.MODEL_CALL,
            payload={"phase": Phase.REFLECT.value, "prompt": prompt},
        )
        reflection = await self._recovery.with_recovery(
            "reflect_on_results",
            self._agent_func,
            prompt,
            state,
            failure_type=FailureType.MALFORMED_OUTPUT,
        )
        self._require_budget().record_model_call()
        state.facts["last_reflection"] = reflection
        self._record_event(
            run.run_id,
            run.current_iteration,
            EventType.MODEL_RESPONSE,
            payload={"phase": Phase.REFLECT.value, "response": reflection},
        )
        self._record_event(
            run.run_id,
            run.current_iteration,
            EventType.BUDGET_UPDATE,
            payload=self._require_budget().state.model_dump(mode="json"),
        )

    async def _decide(self, run: LoopRun, state: LoopState) -> Decision:
        """DECIDE phase: apply stopping rules."""
        return self._require_stopping().evaluate(
            budget=self._require_budget(),
            all_criteria_met=self._all_criteria_met,
            stagnation_count=state.stagnation_count,
        )

    async def resume(self, run_id: str) -> tuple[LoopRun, LoopState] | None:
        """Resume an interrupted run from its latest checkpoint."""
        resumed = await self._checkpoints.resume_run(run_id)
        if resumed is None:
            return None

        run, state = resumed
        self._previous_progress_score = state.progress_score
        return await self._run_loop(
            run,
            state,
            evaluators=None,
            tools=None,
            emit_run_started=False,
        )

    async def _run_phase(
        self,
        run: LoopRun,
        state: LoopState,
        phase: Phase,
        phase_func: Callable[[LoopRun, LoopState], Awaitable[None]],
        *,
        buffer: bool = True,
    ) -> None:
        state.phase = phase
        self._emit_phase_event(run, phase, EventType.PHASE_ENTER, buffer=buffer)
        await phase_func(run, state)
        self._emit_phase_event(run, phase, EventType.PHASE_EXIT, buffer=buffer)

    async def _run_decide_phase(self, run: LoopRun, state: LoopState) -> Decision:
        state.phase = Phase.DECIDE
        self._emit_phase_event(run, Phase.DECIDE, EventType.PHASE_ENTER, buffer=False)
        decision = await self._decide(run, state)
        self._emit_phase_event(run, Phase.DECIDE, EventType.PHASE_EXIT, buffer=False)
        return decision

    def _emit_phase_event(
        self,
        run: LoopRun,
        phase: Phase,
        event_type: EventType,
        *,
        buffer: bool,
    ) -> None:
        payload = {"phase": phase.value}
        if buffer:
            self._buffer_event(run.run_id, run.current_iteration, event_type, payload=payload)
            return
        self._record_event(run.run_id, run.current_iteration, event_type, payload=payload)

    def _buffer_event(
        self,
        run_id: str,
        iteration: int,
        event_type: EventType,
        *,
        payload: dict[str, Any] | None = None,
    ) -> LoopEvent:
        event = LoopEvent(
            run_id=run_id,
            iteration=iteration,
            event_type=event_type,
            payload=payload or {},
        )
        self._current_events.append(event)
        return event

    def _record_event(
        self,
        run_id: str,
        iteration: int,
        event_type: EventType,
        *,
        payload: dict[str, Any] | None = None,
    ) -> LoopEvent:
        event = LoopEvent(
            run_id=run_id,
            iteration=iteration,
            event_type=event_type,
            payload=payload or {},
        )
        self._recorder.record(event)
        return event

    async def _invoke_tool(self, tool: ToolFunc, tool_args: Any) -> Any:
        if isinstance(tool_args, dict):
            result = tool(**tool_args)
        elif isinstance(tool_args, tuple):
            result = tool(*tool_args)
        elif tool_args is None:
            result = tool()
        else:
            result = tool(tool_args)

        if inspect.isawaitable(result):
            return await result
        return result

    async def _invoke_evaluator(self, evaluator: EvaluatorFunc, state: LoopState) -> Any:
        result = evaluator(state)
        if inspect.isawaitable(result):
            return await result
        return result

    def _normalize_evaluation_result(
        self,
        evaluator: EvaluatorFunc,
        result: Any,
    ) -> EvaluationResult:
        if isinstance(result, EvaluationResult):
            return result
        if isinstance(result, dict):
            payload = dict(result)
            payload.setdefault(
                "evaluator_name",
                getattr(evaluator, "__name__", evaluator.__class__.__name__),
            )
            return EvaluationResult.model_validate(payload)
        raise TypeError("Evaluators must return EvaluationResult or dict payloads")

    def _resolve_tool_args(self, state: LoopState, action_name: str) -> Any:
        tool_args = state.facts.get("tool_args", {})
        if isinstance(tool_args, dict):
            return tool_args.get(action_name)
        return None

    def _coerce_payload_value(self, value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, list):
            return [self._coerce_payload_value(item) for item in value]
        if isinstance(value, dict):
            return {str(key): self._coerce_payload_value(item) for key, item in value.items()}
        return str(value)

    def _require_budget(self) -> BudgetManager:
        if self._budget is None:
            raise RuntimeError("Budget manager is not initialized")
        return self._budget

    def _require_stopping(self) -> StoppingPolicy:
        if self._stopping is None:
            raise RuntimeError("Stopping policy is not initialized")
        return self._stopping
