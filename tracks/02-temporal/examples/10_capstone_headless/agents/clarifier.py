"""Clarifier agent — narrows a vague topic into one researchable question.

Stage one of the capstone pipeline. No tools, no structured output: the
agent emits a single-sentence question that the Researcher consumes
verbatim. Keeping this agent stateless and small means the entire stage
runs as a single `model_request` activity in the workflow history.
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import TemporalAgent

from learn_pydantic_ai import FLASH

_base = Agent(
    model=FLASH,
    name="capstone_clarifier",
    instructions=(
        "You turn vague topics into ONE specific, researchable question. "
        "Reply with just the question — no preamble, no explanation. "
        "Keep it under 20 words."
    ),
)

clarifier = TemporalAgent(_base)
