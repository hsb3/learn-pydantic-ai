"""Capstone writer agent — produces the final report.

Minimal agent, default `TemporalAgent` config. The retry / timeout
defaults are fine here because this stage is just a single
forward-pass call with no tools.
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import TemporalAgent

from learn_pydantic_ai import FLASH

_base = Agent(
    model=FLASH,
    name="capstone_writer",
    instructions=(
        "Write a 3-paragraph report from the research findings. "
        "First paragraph: summary. Second: key data points. Third: takeaway."
    ),
)

writer = TemporalAgent(_base)
