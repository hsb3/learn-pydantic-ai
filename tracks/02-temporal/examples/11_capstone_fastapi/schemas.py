"""Lesson 11 — request/response models for the FastAPI front-end.

FastAPI uses these to validate JSON bodies and serialize responses.
"""

from __future__ import annotations

from pydantic import BaseModel


class ResearchRequest(BaseModel):
    """POST /research body — the topic to research."""

    topic: str


class ResearchHandle(BaseModel):
    """POST /research response — handle the client uses to poll."""

    workflow_id: str


class ResearchStatus(BaseModel):
    """GET /research/{id} response — live workflow state."""

    workflow_id: str
    status: str
    draft: str | None = None
    final_report: str | None = None


class ApprovalPayload(BaseModel):
    """POST /research/{id}/approve body — reviewer's optional note."""

    note: str = ""
