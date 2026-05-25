"""Sub-package holding the three TemporalAgents for the capstone.

Each module exposes a single module-level `TemporalAgent` — the workflow
imports them and lists all three in `__pydantic_ai_agents__` so the
plugin can register their auto-generated activities at worker startup.
"""

from __future__ import annotations

from agents.clarifier import clarifier
from agents.researcher import researcher
from agents.writer import writer

__all__ = ["clarifier", "researcher", "writer"]
