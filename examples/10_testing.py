"""10 — Testing with TestModel and FunctionModel.

Two test doubles ship with pydantic-ai:

- `TestModel` — auto-generates valid output (just returns "a"-style text and
  invents arguments for any tools). Great for "does my agent wire up?" tests.

- `FunctionModel` — you write the response function. Use when you need
  exact behavior: a specific text answer, a particular tool call,
  triggering a retry, etc.

Both plug in via `agent.override(model=...)`. Never set `agent.model = ...`
directly — the override context manager restores the real model afterwards.

Run with:  uv run pytest examples/10_testing.py -v
"""

from __future__ import annotations

from pydantic import BaseModel
from pydantic_ai import Agent, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.models.test import TestModel

from _common import FLASH


class Weather(BaseModel):
    city: str
    summary: str
    fahrenheit: int


weather_agent = Agent(FLASH, output_type=Weather)


@weather_agent.tool_plain
def lookup_weather(city: str) -> dict[str, str | int]:
    """Pretend external weather API."""
    return {"city": city, "summary": "sunny", "fahrenheit": 72}


# ─── TestModel: zero-effort smoke test ──────────────────────────────────────


def test_agent_wires_up_with_testmodel() -> None:
    """TestModel auto-produces a valid Weather instance — no real model call."""
    with weather_agent.override(model=TestModel()):
        result = weather_agent.run_sync("Anything")
    assert isinstance(result.output, Weather)


# ─── FunctionModel: assert exact behavior ───────────────────────────────────


def _scripted_model(messages, info):
    """Two-step scripted response: first call the tool, then return Weather."""
    # `info.function_tools` tells us which tools the agent registered. Pick
    # the right call based on whether the tool has already returned.
    has_tool_return = any(
        p.part_kind == "tool-return" for m in messages for p in m.parts
    )
    if not has_tool_return:
        return ModelResponse(
            parts=[ToolCallPart(tool_name="lookup_weather", args={"city": "Paris"})]
        )
    # After the tool returns, emit the structured output by calling the
    # auto-generated `final_result` tool.
    return ModelResponse(
        parts=[
            ToolCallPart(
                tool_name="final_result",
                args={"city": "Paris", "summary": "sunny", "fahrenheit": 72},
            )
        ]
    )


def test_agent_calls_lookup_weather() -> None:
    with weather_agent.override(model=FunctionModel(_scripted_model)):
        result = weather_agent.run_sync("Weather in Paris?")
    assert result.output == Weather(city="Paris", summary="sunny", fahrenheit=72)
    # Confirm the tool actually ran.
    tool_calls = [
        p
        for m in result.all_messages()
        for p in m.parts
        if type(p).__name__ == "ToolCallPart" and p.tool_name == "lookup_weather"
    ]
    assert len(tool_calls) == 1


# ─── Simple agent without tools ──────────────────────────────────────────────

plain_agent = Agent(FLASH, instructions="reply concisely")


def test_plain_agent_with_function_model() -> None:
    def model_fn(messages, info):
        return ModelResponse(parts=[TextPart(content="mocked!")])

    with plain_agent.override(model=FunctionModel(model_fn)):
        result = plain_agent.run_sync("hi")
    assert result.output == "mocked!"
