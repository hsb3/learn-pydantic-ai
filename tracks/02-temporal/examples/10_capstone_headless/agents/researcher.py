"""Researcher agent — answers the clarified question via fake lookup tools.

Stage two. Real research would use the `WebSearch` capability or an HTTP
tool; for the lesson, we hard-code a tiny fact table so the workflow is
deterministic and the test can run offline. Each tool call is lifted
into its own activity in the workflow history.
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import TemporalAgent

from learn_pydantic_ai import FLASH

_FACTS_GDP: dict[str, str] = {
    "Japan": "$4.2T (2023)",
    "France": "$3.0T (2023)",
    "Brazil": "$2.1T (2023)",
}
_FACTS_POPULATION: dict[str, str] = {
    "Japan": "125M",
    "France": "68M",
    "Brazil": "215M",
}

_base = Agent(
    model=FLASH,
    name="capstone_researcher",
    instructions=(
        "Answer the question using the available lookup tools when relevant. "
        "Be terse — 2-3 sentences max. Cite the tool result verbatim."
    ),
)


@_base.tool_plain
def gdp(country: str) -> str:
    """Return GDP for a country (hardcoded reference data)."""
    return _FACTS_GDP.get(country, f"No GDP data for {country}")


@_base.tool_plain
def population(country: str) -> str:
    """Return population for a country (hardcoded reference data)."""
    return _FACTS_POPULATION.get(country, f"No population data for {country}")


# Wrap AFTER tools are registered. TemporalAgent inspects the toolset to
# lift each tool into its own activity at worker startup.
researcher = TemporalAgent(_base)
