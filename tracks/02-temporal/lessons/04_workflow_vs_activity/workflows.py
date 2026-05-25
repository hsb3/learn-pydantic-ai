"""Lesson 04 — same shape as Lesson 03, but the agent has ONE tool.

The point of this lesson is the Temporal UI history: after you run the
workflow, you will see TWO activities scheduled and completed for a single
agent call:

1. `model_request` — the LLM call that decides "I should call get_weather".
2. `get_weather` — the tool invocation itself, lifted into an activity
   automatically by `TemporalAgent`.

And then the model is called a second time to turn the tool's return value
into the final user-facing string — so the history actually shows:

    ActivityTaskScheduled (model_request)
    ActivityTaskCompleted (model_request)
    ActivityTaskScheduled (get_weather)
    ActivityTaskCompleted (get_weather)
    ActivityTaskScheduled (model_request)
    ActivityTaskCompleted (model_request)
    WorkflowExecutionCompleted

The workflow itself contributes only `WorkflowTaskCompleted` events
between activity calls — orchestration, not side-effecting work.

The rule: **model calls = activity, tool calls = activity, orchestration
= workflow.** Anything you want durable, retryable, and memoized to history
goes through an activity; anything that picks the next step stays in the
workflow.
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import PydanticAIWorkflow, TemporalAgent
from temporalio import workflow

from learn_pydantic_ai import FLASH

# Hardcoded weather table — deterministic so the lesson always renders the
# same history. A real tool would call an HTTP API; Temporal would still
# wrap it in an activity, so retries + timeouts come for free.
_WEATHER: dict[str, str] = {
    "london": "rainy, 12C",
    "tokyo": "sunny, 22C",
    "san francisco": "foggy, 15C",
}

_base = Agent(
    model=FLASH,
    name="weather_agent",
    instructions=(
        "You answer weather questions. When asked, call `get_weather` "
        "with the city name, then summarize the result in one sentence."
    ),
)


@_base.tool_plain
def get_weather(city: str) -> str:
    """Return current weather for `city`. Returns a short status string."""
    return _WEATHER.get(city.lower(), f"no data for {city}")


# Wrap AFTER tools are registered. TemporalAgent inspects the agent's
# toolset to lift each tool into its own activity.
weather_agent = TemporalAgent(_base)


@workflow.defn
class WeatherWorkflow(PydanticAIWorkflow):
    """One agent call. The agent will internally schedule two model
    activities and one tool activity — visible in the Temporal UI."""

    __pydantic_ai_agents__ = [weather_agent]

    @workflow.run
    async def run(self, city: str) -> str:
        # `workflow.logger` is the deterministic-safe replacement for
        # `print()` / `logging.info()` inside workflow code.
        workflow.logger.info("WeatherWorkflow running for city=%s", city)
        result = await weather_agent.run(f"What's the weather in {city}?")
        return result.output
