"""Lesson 09 — observability with Logfire.

A multi-tool researcher agent inside a Temporal workflow. The workflow body
itself is intentionally trivial — one `await researcher.run(...)` — because
the *interesting* thing in this lesson is what `LogfirePlugin` records about
that single call:

- The workflow execution becomes a single Logfire trace.
- Each model request the agent makes is a span inside it.
- Each tool call (`look_up_population`, `look_up_currency`) is a child span.
- Each HTTP request to the model provider is a child span underneath the
  model-request span (thanks to `logfire.instrument_httpx`).

`LogfirePlugin` lives in `worker.py`, not here — the workflow code stays
deterministic and provider-agnostic.
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import PydanticAIWorkflow, TemporalAgent
from temporalio import workflow

from learn_pydantic_ai import FLASH

# Hard-coded fact tables. Deterministic so every run produces the same trace
# tree — useful when you're learning to read Logfire spans.
_FACTS_POPULATION: dict[str, str] = {
    "Tokyo": "13.96M",
    "Paris": "2.16M",
    "São Paulo": "12.33M",
}
_FACTS_CURRENCY: dict[str, str] = {
    "Japan": "JPY",
    "France": "EUR",
    "Brazil": "BRL",
}


# `name=` is required — Temporal derives activity names from it.
_base = Agent(
    model=FLASH,
    name="researcher",
    instructions="Use the tools to answer concisely.",
)


@_base.tool_plain
def look_up_population(city: str) -> str:
    """Return a string describing the population of `city`."""
    return _FACTS_POPULATION.get(city, f"No data for {city}")


@_base.tool_plain
def look_up_currency(country: str) -> str:
    """Return the ISO currency code used in `country`."""
    return _FACTS_CURRENCY.get(country, f"No data for {country}")


# Wrap AFTER tools are registered so `TemporalAgent` can lift each tool into
# its own activity.
researcher = TemporalAgent(_base)


@workflow.defn
class ResearchWorkflow(PydanticAIWorkflow):
    """Two-tool researcher. One workflow call typically schedules:

    - 2-3 `model_request` activities (the agent decides → calls tools → answers)
    - 1 `look_up_population` activity
    - 1 `look_up_currency` activity

    With `LogfirePlugin` enabled on the worker, every one of those activities
    also emits a Logfire span — and the model-request activities have child
    HTTP spans showing the real network call to the provider.
    """

    __pydantic_ai_agents__ = [researcher]

    @workflow.run
    async def run(self, question: str) -> str:
        # Deterministic-safe logger. NEVER call `print()` or `logfire.info()`
        # directly inside a `@workflow.run` body — the sandbox will reject it.
        workflow.logger.info("ResearchWorkflow running for question=%r", question)
        result = await researcher.run(question)
        return result.output
