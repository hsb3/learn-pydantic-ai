"""Writer agent — turns research findings into a short report.

Stage three. Reads the researcher's distilled summary and emits a tight,
human-readable paragraph that the workflow returns once a reviewer
approves. No tools — a single `model_request` activity per run.
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import TemporalAgent

from learn_pydantic_ai import FLASH

_base = Agent(
    model=FLASH,
    name="capstone_writer",
    instructions=(
        "Turn the research findings into a short report (3-4 sentences). "
        "Plain prose, no headings, no bullet points. Be concise and direct."
    ),
)

writer = TemporalAgent(_base)
