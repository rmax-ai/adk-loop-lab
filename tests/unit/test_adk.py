"""Tests for ADK adapters."""

import pytest

from adk_loop_lab.adk.agents import create_agent
from adk_loop_lab.adk.compatibility import check_adk_version, get_default_model, require_adk_version
from adk_loop_lab.adk.runner import adk_event_to_loop_event, create_runner
from adk_loop_lab.models import EventType


class TestCompatibility:
    def test_check_version_returns_tuple(self) -> None:
        version = check_adk_version()
        assert isinstance(version, tuple)
        assert len(version) == 3
        # Current install should be 2.2.x
        assert version >= (2, 2, 0)

    def test_require_version_passes(self) -> None:
        require_adk_version()  # Should not raise

    def test_require_version_fails_for_future(self) -> None:
        with pytest.raises(RuntimeError, match="below minimum"):
            require_adk_version(min_version=(99, 0, 0))

    def test_default_model(self) -> None:
        model = get_default_model()
        assert isinstance(model, str)
        assert "gemini" in model.lower()


class TestAgentFactory:
    def test_create_basic_agent(self) -> None:
        agent = create_agent("test_agent", "You are a test assistant.")
        assert agent.name == "test_agent"

    def test_create_agent_with_tools(self) -> None:
        async def dummy_tool(x: str) -> str:
            return x

        agent = create_agent("tooled", "Test", tools=[dummy_tool])
        assert agent.name == "tooled"

    def test_create_agent_with_output_key(self) -> None:
        agent = create_agent("with_key", "Test", output_key="my_result")
        assert agent.name == "with_key"


class TestRunner:
    def test_create_runner(self) -> None:
        agent = create_agent("runner_test", "Test")
        runner = create_runner(agent)
        assert runner is not None
        assert runner.app_name == "adk-loop-lab"

    def test_event_conversion(self) -> None:
        class MockEvent:
            author = "test_agent"
            invocation_id = "inv-1"

        event = adk_event_to_loop_event(MockEvent(), "run-1", 3)
        assert event.run_id == "run-1"
        assert event.iteration == 3
        assert event.event_type == EventType.MODEL_CALL
        assert event.actor == "test_agent"
        assert event.payload["adk_event_type"] == "MockEvent"

    def test_event_conversion_no_author(self) -> None:
        class MockEvent:
            pass

        event = adk_event_to_loop_event(MockEvent(), "run-1", 1)
        assert event.actor == "unknown"
