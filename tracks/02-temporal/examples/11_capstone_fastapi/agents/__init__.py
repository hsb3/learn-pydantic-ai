"""Capstone agents — clarifier, researcher, writer.

Each module exports one `TemporalAgent` configured to demonstrate a
specific track concept:

    clarifier.py   — base agent + `activity_config` retry policy (Lesson 05)
    researcher.py  — tools + per-tool `tool_activity_config` (Lesson 05) +
                     `event_stream_handler` (Lesson 06)
    writer.py      — minimal agent, default config

They're combined in `../workflow.py` into a single durable pipeline.
"""

from agents.clarifier import clarifier
from agents.researcher import researcher
from agents.writer import writer

__all__ = ["clarifier", "researcher", "writer"]
