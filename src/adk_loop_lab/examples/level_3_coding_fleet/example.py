"""Example 3: resumable multi-agent coding loop."""

from __future__ import annotations

import asyncio
import json
import shutil
import sqlite3
import subprocess
import tempfile
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any

from adk_loop_lab.adk.runner import create_runner, run_agent
from adk_loop_lab.events.recorder import EventRecorder
from adk_loop_lab.examples.level_3_coding_fleet.agents import (
    FAKE_SCRIPT,
    create_implementer_agent,
    create_observer_agent,
    create_planner_agent,
    get_fake_response,
    setup_fake_responses,
)
from adk_loop_lab.examples.level_3_coding_fleet.orchestrator import (
    AgentRoute,
    CodingOrchestrator,
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
from adk_loop_lab.tools.shell import SandboxShell


def _attach_fake_callback(*agents: Any) -> None:
    callback = FAKE_SCRIPT.as_callback()
    for agent in agents:
        agent.before_model_callback = callback


class _CursorAdapter:
    """Async-shaped wrapper around a sqlite3 cursor."""

    def __init__(self, cursor: sqlite3.Cursor) -> None:
        self._cursor = cursor

    async def fetchone(self) -> tuple[Any, ...] | None:
        return self._cursor.fetchone()  # type: ignore[no-any-return]

    async def fetchall(self) -> list[tuple[Any, ...]]:
        return self._cursor.fetchall()

    async def close(self) -> None:
        self._cursor.close()


class _ConnectionAdapter:
    """Async-shaped wrapper around a sqlite3 connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    async def execute(
        self,
        sql: str,
        parameters: tuple[Any, ...] = (),
    ) -> _CursorAdapter:
        cursor = self._connection.execute(sql, parameters)
        return _CursorAdapter(cursor)

    async def commit(self) -> None:
        self._connection.commit()

    async def rollback(self) -> None:
        self._connection.rollback()

    async def close(self) -> None:
        self._connection.close()


class _ExampleStateStore:
    """Small sqlite3-backed store compatible with LoopController needs."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._connection: _ConnectionAdapter | None = None

    async def initialize(self) -> None:
        db_file = Path(self._db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        raw_connection = sqlite3.connect(self._db_path)
        self._connection = _ConnectionAdapter(raw_connection)
        connection = self._require_connection()
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                example_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                data TEXT NOT NULL
            )
            """
        )
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS loop_states (
                run_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                FOREIGN KEY (run_id) REFERENCES runs (run_id) ON DELETE CASCADE
            )
            """
        )
        await connection.commit()

    async def save_run(self, run: LoopRun) -> None:
        connection = self._require_connection()
        await connection.execute(
            """
            INSERT INTO runs (run_id, example_id, status, created_at, updated_at, data)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                example_id = excluded.example_id,
                status = excluded.status,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                data = excluded.data
            """,
            (
                run.run_id,
                run.example_id,
                run.status.value,
                run.created_at.isoformat(),
                run.updated_at.isoformat(),
                run.model_dump_json(),
            ),
        )
        await connection.commit()

    async def save_state(self, run_id: str, state: LoopState) -> None:
        connection = self._require_connection()
        await connection.execute(
            """
            INSERT INTO loop_states (run_id, data)
            VALUES (?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                data = excluded.data
            """,
            (run_id, state.model_dump_json()),
        )
        await connection.commit()

    async def close(self) -> None:
        if self._connection is None:
            return
        await self._connection.close()
        self._connection = None

    def _require_connection(self) -> _ConnectionAdapter:
        if self._connection is None:
            raise RuntimeError("Example state store is not initialized")
        return self._connection


def _parse_plan(raw_plan: str) -> dict[str, Any]:
    """Parse planner output into a validated dict payload."""
    try:
        payload = json.loads(raw_plan)
    except json.JSONDecodeError:
        return {"action": "clarify", "files": [], "description": raw_plan}

    files = payload.get("files", [])
    if not isinstance(files, list):
        files = []
    return {
        "action": str(payload.get("action", "clarify")),
        "files": [str(item) for item in files],
        "description": str(payload.get("description", "")),
    }


def _ttl_test_code() -> str:
    """Return the updated fixture test module with TTL coverage."""
    return textwrap.dedent(
        '''\
        """Tests for KVStore."""

        import time

        from kvstore import KVStore


        class TestKVStore:
            def test_set_and_get(self) -> None:
                store = KVStore()
                store.set("a", 1)
                assert store.get("a") == 1

            def test_get_missing(self) -> None:
                store = KVStore()
                assert store.get("nonexistent") is None

            def test_delete(self) -> None:
                store = KVStore()
                store.set("a", 1)
                assert store.delete("a")
                assert not store.delete("a")

            def test_exists(self) -> None:
                store = KVStore()
                store.set("a", 1)
                assert store.exists("a")
                assert not store.exists("b")

            def test_keys(self) -> None:
                store = KVStore()
                store.set("a", 1)
                store.set("b", 2)
                assert set(store.keys()) == {"a", "b"}

            def test_set_without_ttl_remains_backward_compatible(self) -> None:
                store = KVStore()
                store.set("session", {"user": "alice"})
                assert store.get("session") == {"user": "alice"}

            def test_ttl_expiration_returns_none(self) -> None:
                store = KVStore()
                store.set("token", "abc", ttl_seconds=0.01)
                time.sleep(0.02)
                assert store.get("token") is None

            def test_expired_keys_are_removed_from_exists_and_keys(self) -> None:
                store = KVStore()
                store.set("short", "x", ttl_seconds=0.01)
                store.set("long", "y")
                time.sleep(0.02)
                assert not store.exists("short")
                assert set(store.keys()) == {"long"}
        '''
    )


def _sandbox_test_command() -> str:
    """Build a deterministic sandbox test runner command."""
    script = textwrap.dedent(
        """\
        import importlib.util
        import inspect
        import pathlib
        import sys

        root = pathlib.Path('.').resolve()
        sys.path.insert(0, str(root))

        spec = importlib.util.spec_from_file_location(
            'sandbox_test_kvstore',
            root / 'tests' / 'test_kvstore.py',
        )
        module = importlib.util.module_from_spec(spec)
        assert spec is not None and spec.loader is not None
        spec.loader.exec_module(module)

        test_class = module.TestKVStore
        failures = []
        for name, member in inspect.getmembers(test_class, predicate=inspect.isfunction):
            if not name.startswith('test_'):
                continue
            instance = test_class()
            try:
                member(instance)
            except Exception as exc:
                failures.append(f'{name}: {exc}')

        if failures:
            print('\\n'.join(failures))
            raise SystemExit(1)

        print('all sandbox tests passed')
        """
    ).strip()
    return f"python3 -c {json.dumps(script)}"


def _initialize_sandbox_repo(sandbox_dir: str) -> None:
    """Initialize a git repository for patch generation inside the sandbox."""
    commands = [
        ["git", "init"],
        ["git", "config", "user.email", "example@local.test"],
        ["git", "config", "user.name", "Example Runner"],
        ["git", "add", "."],
        ["git", "commit", "-m", "Initial sandbox baseline"],
    ]
    for command in commands:
        subprocess.run(
            command,
            cwd=sandbox_dir,
            check=True,
            capture_output=True,
            text=True,
        )


def _extract_code(response: str) -> str | None:
    """Extract Python code from a markdown response."""
    if "```python" in response:
        block = response.split("```python", maxsplit=1)[1]
        return block.split("```", maxsplit=1)[0].strip()
    if "```" in response:
        block = response.split("```", maxsplit=1)[1]
        return block.split("```", maxsplit=1)[0].strip()
    stripped = response.strip()
    return stripped or None


def _build_evaluators(
    orchestrator: CodingOrchestrator,
) -> list[Callable[[LoopState], EvaluationResult]]:
    def evaluate_tests(state: LoopState) -> EvaluationResult:
        test_results = state.facts.get("test_results", {})
        exit_code = int(test_results.get("exit_code", 1))
        passed = exit_code == 0
        return EvaluationResult(
            evaluator_name="tests",
            status=EvaluatorStatus.PASS if passed else EvaluatorStatus.FAIL,
            score=1.0 if passed else 0.0,
            summary=f"pytest exit_code={exit_code}",
            failures=[] if passed else [str(test_results.get("stdout", "tests failed"))],
        )

    def evaluate_requirements(state: LoopState) -> EvaluationResult:
        kvstore = orchestrator.fs.read("kvstore.py") if orchestrator.fs.exists("kvstore.py") else ""
        has_ttl = "ttl_seconds" in kvstore and "_is_expired" in kvstore and "time.time()" in kvstore
        return EvaluationResult(
            evaluator_name="requirements",
            status=EvaluatorStatus.PASS if has_ttl else EvaluatorStatus.FAIL,
            score=1.0 if has_ttl else 0.0,
            summary="TTL support detected in sandboxed KVStore.",
            failures=[] if has_ttl else ["KVStore does not appear to implement TTL support."],
        )

    return [evaluate_tests, evaluate_requirements]


async def run_example(
    use_fake_model: bool = True,
    *,
    base_dir: str = "var/runs",
    db_path: str = "var/state/level_3_coding_fleet.db",
    model_name: str | None = None,
    max_iterations: int | None = None,
) -> tuple[LoopRun, LoopState]:
    """Run the coding fleet example end-to-end."""
    Path(base_dir).mkdir(parents=True, exist_ok=True)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    fixture_repo = Path(__file__).parents[4] / "tests" / "fixtures" / "target_repo"
    sandbox = tempfile.mkdtemp(prefix="coding_sandbox_")
    shutil.copytree(fixture_repo, sandbox, dirs_exist_ok=True)
    _initialize_sandbox_repo(sandbox)

    store = SqliteStateStore(db_path)
    await store.initialize()
    recorder = EventRecorder(base_dir=base_dir)

    run = LoopRun(
        example_id="level_3_coding_fleet",
        goal="Add expiration/TTL support to KVStore while preserving backward compatibility.",
        budgets=BudgetConfig(
            max_iterations=max_iterations or 6,
            max_model_calls=30,
            stagnation_threshold=3,
        ),
    )
    state = LoopState(
        facts={
            "sandbox_dir": sandbox,
            "task": run.goal,
            "files": [],
            "planned_route": None,
            "test_results": {},
            "failed_approaches": [],
        }
    )

    orchestrator = CodingOrchestrator(sandbox)
    shell = SandboxShell(sandbox)

    observer = create_observer_agent(model=model_name)
    planner = create_planner_agent(model=model_name)
    implementer = create_implementer_agent(model=model_name)
    observer_runner = None
    planner_runner = None
    implementer_runner = None
    if use_fake_model:
        setup_fake_responses()
        _attach_fake_callback(observer, planner, implementer)
    else:
        observer_runner = create_runner(observer, app_name="level-3-observer")
        planner_runner = create_runner(planner, app_name="level-3-planner")
        implementer_runner = create_runner(implementer, app_name="level-3-implementer")

    async def run_coding_agent(
        runner: Any | None,
        session_id: str,
        prompt: str,
    ) -> str:
        if use_fake_model:
            return get_fake_response(prompt)
        if runner is None:
            raise ValueError("Runner is required when fake mode is disabled.")
        return await run_agent(runner, "user", session_id, prompt)

    async def agent_func(_: str, current_state: LoopState) -> str:
        if current_state.phase is Phase.DISCOVER:
            files = orchestrator.fs.list_dir(".")
            tests = orchestrator.fs.list_dir("tests") if orchestrator.fs.exists("tests") else []
            current_state.facts["files"] = files
            current_state.facts["test_files"] = tests
            return f"Files: {files}; tests: {tests}"

        if current_state.phase is Phase.PLAN:
            kvstore = orchestrator.fs.read("kvstore.py")
            investigation = await run_coding_agent(
                observer_runner,
                f"{run.run_id}-observer",
                (
                    "investigate the repository for the TTL task.\n\n"
                    f"task: {run.goal}\n\ncurrent kvstore.py:\n{kvstore}"
                ),
            )
            test_design = await run_coding_agent(
                observer_runner,
                f"{run.run_id}-test-design",
                (
                    "design tests for the TTL task.\n\n"
                    f"task: {run.goal}\n\nexisting tests:\n"
                    f"{orchestrator.fs.read('tests/test_kvstore.py')}"
                ),
            )
            plan_text = await run_coding_agent(
                planner_runner,
                f"{run.run_id}-planner",
                (
                    "plan the next bounded action for the coding task.\n\n"
                    f"task: {run.goal}\ninvestigation: {investigation}\n"
                    f"test design: {test_design}"
                ),
            )
            plan = _parse_plan(plan_text)
            route = orchestrator.route(plan)
            approach_hash = orchestrator.plan_hash(plan)
            current_state.facts["investigation"] = investigation
            current_state.facts["test_design"] = test_design
            current_state.facts["current_plan"] = plan
            current_state.facts["planned_route"] = route.value
            current_state.facts["approach_hash"] = approach_hash
            return json.dumps(
                {
                    "route": route.value,
                    "approach_hash": approach_hash,
                    "plan": plan,
                }
            )

        if current_state.phase is Phase.EXECUTE:
            plan = current_state.facts.get("current_plan", {})
            if not isinstance(plan, dict):
                return "No executable plan."

            route_value = str(current_state.facts.get("planned_route", AgentRoute.CLARIFY.value))
            if route_value != AgentRoute.IMPLEMENT.value:
                return f"Route {route_value} does not execute code changes."

            approach_hash = str(current_state.facts.get("approach_hash", ""))
            if orchestrator.check_failure_repetition(approach_hash):
                current_state.facts["blocked_reason"] = "Repeated failure detected"
                return f"BLOCKED: approach {approach_hash} already failed repeatedly."

            response = await run_coding_agent(
                implementer_runner,
                f"{run.run_id}-implementer",
                (
                    "implement the change.\n\n"
                    f"plan: {json.dumps(plan)}\n\ncurrent kvstore.py:\n"
                    f"{orchestrator.fs.read('kvstore.py')}"
                ),
            )
            new_code = _extract_code(response)
            if new_code:
                orchestrator.fs.write("kvstore.py", new_code + "\n")
                orchestrator.fs.write("tests/test_kvstore.py", _ttl_test_code())
                orchestrator.completed_actions.append(str(plan.get("action", "")))
            current_state.facts["implementation"] = response
            return response

        if current_state.phase is Phase.REFLECT:
            return str(current_state.facts.get("verification_summary", ""))

        return ""

    def evaluate_failure_memory(state: LoopState) -> EvaluationResult:
        blocked = bool(state.facts.get("blocked_reason"))
        return EvaluationResult(
            evaluator_name="failure_memory",
            status=EvaluatorStatus.FAIL if blocked else EvaluatorStatus.PASS,
            score=0.0 if blocked else 1.0,
            summary="Approach repetition guard checked.",
            failures=[] if not blocked else [str(state.facts.get("blocked_reason"))],
        )

    async def verify_sandbox(current_state: LoopState) -> EvaluationResult:
        exit_code, stdout, stderr = shell.run(_sandbox_test_command(), timeout=60)
        output = (stdout + "\n" + stderr).strip()
        current_state.facts["test_results"] = {
            "exit_code": exit_code,
            "stdout": output[-1000:],
        }
        if exit_code != 0:
            approach_hash = str(current_state.facts.get("approach_hash", ""))
            orchestrator.record_failure(
                approach_hash=approach_hash,
                error=output,
                iteration=run.current_iteration,
            )
            current_state.facts["failed_approaches"] = [
                {
                    "approach_hash": record.approach_hash,
                    "retry_count": record.retry_count,
                    "blocked": record.blocked,
                    "error_signature": record.error_signature,
                }
                for record in orchestrator.failure_history
            ]
        current_state.facts["verification_summary"] = f"pytest exit={exit_code}"
        return EvaluationResult(
            evaluator_name="sandbox_pytest",
            status=EvaluatorStatus.PASS if exit_code == 0 else EvaluatorStatus.FAIL,
            score=1.0 if exit_code == 0 else 0.0,
            summary=f"Sandbox tests exit_code={exit_code}",
            failures=[] if exit_code == 0 else [output[-400:] or "sandbox tests failed"],
        )

    controller = LoopController(store, recorder, agent_func=agent_func)
    evaluators: list[Callable[[LoopState], Any]] = [
        verify_sandbox,
        *_build_evaluators(orchestrator),
        evaluate_failure_memory,
    ]
    final_run, final_state = await controller.run(run, state, evaluators=evaluators)

    patch = orchestrator.get_patch()
    print("\n" + "=" * 60)
    print("EXAMPLE 3: MULTI-AGENT CODING LOOP")
    print("=" * 60)
    print(f"\nPatch:\n{patch}" if patch else "\nNo patch generated")
    print(f"\nStop decision: {final_run.last_decision}")
    print(f"Iterations: {final_run.current_iteration}")
    print(f"Completed actions: {orchestrator.completed_actions}")
    print(f"Failed approaches: {len(orchestrator.failure_history)}")

    shutil.rmtree(sandbox, ignore_errors=True)
    await store.close()
    return final_run, final_state


if __name__ == "__main__":
    asyncio.run(run_example())
