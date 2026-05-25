"""Capstone researcher agent — answers questions using lookup tools.

Three track concepts combined here:

    Lesson 04 — `@_base.tool_plain` for two lookup tools (gdp, population)
    Lesson 05 — `tool_activity_config` for tight per-tool timeouts
    Lesson 06 — `event_stream_handler` so each model + tool event is logged
                via `activity.logger` (which Logfire picks up in Lesson 09's
                wiring)
"""

from __future__ import annotations

from collections.abc import AsyncIterable
from datetime import timedelta

from pydantic_ai import Agent, RunContext
from pydantic_ai.durable_exec.temporal import TemporalAgent
from pydantic_ai.messages import AgentStreamEvent
from temporalio import activity
from temporalio.common import RetryPolicy

from learn_pydantic_ai import FLASH

# Hardcoded fact table — keeps the capstone deterministic for the demo.
# A real researcher would call an HTTP API; Temporal would wrap that in an
# activity automatically (Lesson 03).
_GDP: dict[str, str] = {
    "Japan": "$4.2T (2023)",
    "France": "$3.0T (2023)",
    "Brazil": "$2.1T (2023)",
    "India": "$3.7T (2023)",
    "Germany": "$4.5T (2023)",
}
_POPULATION: dict[str, str] = {
    "Japan": "125M",
    "France": "68M",
    "Brazil": "215M",
    "India": "1.43B",
    "Germany": "84M",
}


_base = Agent(
    model=FLASH,
    name="capstone_researcher",
    instructions=(
        "Answer the question. Use `gdp` and `population` tools when relevant. "
        "Cite the values you got back. Be terse — three sentences max."
    ),
)


@_base.tool_plain
def gdp(country: str) -> str:
    """Return the GDP of a country."""
    return _GDP.get(country, f"No GDP data for {country}")


@_base.tool_plain
def population(country: str) -> str:
    """Return the population of a country."""
    return _POPULATION.get(country, f"No population data for {country}")


# Lesson 06 — handler runs as a Temporal activity, so `activity.logger`
# is the right sink. Logfire (Lesson 09) picks these up automatically.
async def _log_events(
    ctx: RunContext[None], stream: AsyncIterable[AgentStreamEvent]
) -> None:
    """Log every model + tool event the researcher emits."""
    async for event in stream:
        kind = event.event_kind
        if kind == "part_delta":  # too noisy for production logs
            continue
        activity.logger.info("researcher event: %s", kind)


# Lesson 05 — base config + per-tool overrides. Lookup tools are fast;
# tighten their timeout so a stuck connection fails quickly and retries.
researcher = TemporalAgent(
    _base,
    event_stream_handler=_log_events,
    activity_config={
        "start_to_close_timeout": timedelta(seconds=60),
        "retry_policy": RetryPolicy(maximum_attempts=3),
    },
    tool_activity_config={
        "<agent>": {
            "gdp": {
                "start_to_close_timeout": timedelta(seconds=5),
                "retry_policy": RetryPolicy(maximum_attempts=2),
            },
            "population": {
                "start_to_close_timeout": timedelta(seconds=5),
                "retry_policy": RetryPolicy(maximum_attempts=2),
            },
        },
    },
)
