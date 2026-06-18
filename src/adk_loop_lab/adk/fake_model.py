"""Fake model adapter for deterministic testing without live API calls.

Uses ADK's before_model_callback to intercept model calls and return
canned LlmResponse objects. This is the recommended ADK v2 approach.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.context import Context
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai.types import Content, Part

_STATE_SCRIPT_KEY = "adk_loop_lab.fake_model_script"


def make_fake_response(text: str) -> LlmResponse:
    """Create a fake ``LlmResponse`` with the given text content."""
    return LlmResponse(
        content=Content(role="model", parts=[Part(text=text)]),
        partial=False,
        turn_complete=True,
    )


def before_model_callback(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> LlmResponse | None:
    """Return a canned response from state-backed script entries when present."""
    script = callback_context.state.get(_STATE_SCRIPT_KEY, [])
    if not isinstance(script, Sequence) or isinstance(script, (str, bytes)):
        return None

    response = _match_script(script, llm_request)
    if response is None:
        return None
    return make_fake_response(response)


class FakeModelScript:
    """Script of canned model responses for deterministic testing."""

    def __init__(self) -> None:
        self._responses: list[tuple[str, str]] = []

    def add(self, prompt_fragment: str, response: str) -> None:
        """Register a canned response for prompts containing the fragment."""
        self._responses.append((prompt_fragment, response))

    def as_callback(
        self,
    ) -> Callable[[Context, LlmRequest], LlmResponse | None]:
        """Return an ADK-compatible before-model callback."""

        def callback(
            callback_context: Context,
            llm_request: LlmRequest,
        ) -> LlmResponse | None:
            callback_context.state[_STATE_SCRIPT_KEY] = list(self._responses)
            response = _match_script(self._responses, llm_request)
            if response is None:
                return None
            return make_fake_response(response)

        return callback


def _match_script(
    script: Sequence[Any],
    llm_request: LlmRequest,
) -> str | None:
    """Return the first configured response whose fragment appears in the prompt."""
    prompt_text = _request_to_text(llm_request)
    for item in script:
        if (
            isinstance(item, tuple)
            and len(item) == 2
            and isinstance(item[0], str)
            and isinstance(item[1], str)
            and item[0] in prompt_text
        ):
            return item[1]
    return None


def _request_to_text(llm_request: LlmRequest) -> str:
    """Collapse request content into plain text for fragment matching."""
    text_parts: list[str] = []
    for content in llm_request.contents:
        for part in content.parts or []:
            if part.text:
                text_parts.append(part.text)
    return "\n".join(text_parts)
