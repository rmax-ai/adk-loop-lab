"""Tests for ADK workflows, callbacks, and fake model adapter."""

from adk_loop_lab.adk.agents import create_agent
from adk_loop_lab.adk.callbacks import create_event_callback, create_model_call_callback
from adk_loop_lab.adk.fake_model import FakeModelScript, make_fake_response
from adk_loop_lab.adk.workflows import (
    generator_critic_workflow,
    parallel_workflow,
    sequential_workflow,
)
from adk_loop_lab.events.recorder import EventRecorder


class TestWorkflows:
    def test_sequential(self) -> None:
        agents = [create_agent(f"a{i}", f"Agent {i}") for i in range(3)]
        workflow = sequential_workflow("test_seq", agents)
        assert workflow.name == "test_seq"

    def test_parallel(self) -> None:
        agents = [create_agent("a1", "A1"), create_agent("a2", "A2")]
        workflow = parallel_workflow("test_par", agents)
        assert workflow.name == "test_par"

    def test_generator_critic(self) -> None:
        gen = create_agent("gen", "Generate content.")
        critic = create_agent("crit", "Critique content.")
        workflow = generator_critic_workflow("test_gc", gen, critic, max_rounds=3)
        assert workflow.name == "test_gc"


class TestCallbacks:
    def test_event_callback_creation(self) -> None:
        recorder = EventRecorder()
        cb = create_event_callback(recorder, "run-1", 1)
        assert callable(cb)

    def test_model_call_callback_creation(self) -> None:
        recorder = EventRecorder()
        cb = create_model_call_callback(recorder, "run-2", 3)
        assert callable(cb)


class TestFakeModel:
    def test_make_fake_response(self) -> None:
        resp = make_fake_response("Hello world")
        assert resp is not None

    def test_script_add_and_match(self) -> None:
        script = FakeModelScript()
        script.add("plan next step", "Execute the patch")
        assert len(script._responses) == 1

    def test_script_as_callback(self) -> None:
        script = FakeModelScript()
        script.add("plan", "Execute")
        cb = script.as_callback()
        assert callable(cb)

    def test_script_first_match(self) -> None:
        script = FakeModelScript()
        script.add("plan", "response-1")
        script.add("replan", "response-2")
        assert script._responses[0][0] == "plan"
        assert script._responses[1][0] == "replan"
