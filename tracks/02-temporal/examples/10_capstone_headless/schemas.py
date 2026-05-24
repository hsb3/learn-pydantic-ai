"""Lesson 10 — Pydantic models shared by the capstone agents.

Plain `BaseModel`s — no Temporal-specific shape. The workflow returns a
final `str` for simplicity, but the intermediate handoffs use these
structured types so each agent's contract is explicit.

Key Classes:
    ClarifiedQuestion: Clarifier -> Researcher handoff.
    ResearchFindings: Researcher -> Writer handoff.
    ApprovalPayload: Note attached to the HITL approval signal.
"""

from __future__ import annotations

from pydantic import BaseModel


class ClarifiedQuestion(BaseModel):
    """Researchable question derived from a vague topic."""

    question: str


class ResearchFindings(BaseModel):
    """Distilled answer to the clarified question."""

    summary: str


class ApprovalPayload(BaseModel):
    """Note the reviewer attaches to the approval signal."""

    note: str = ""
