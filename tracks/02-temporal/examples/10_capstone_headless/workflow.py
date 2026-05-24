"""Lesson 10 — capstone workflow: clarifier -> researcher -> writer + HITL.

Three TemporalAgents collaborate inside a single durable workflow, then
the workflow pauses on `workflow.wait_condition` until a reviewer signals
`approve(...)`. Each agent's model + tool calls become activities — open
the workflow in the Temporal UI to see ~7 activities scheduled across
the three stages.

Key Classes:
    ResearchWorkflow: registers all three agents via
        `__pydantic_ai_agents__` and orchestrates the three stages with
        a final approval gate.

Signals:
    approve(note: str): flips `_approved=True` and stores the note so the
        final report can include reviewer feedback.

Queries:
    status() -> str: live stage marker (clarifying / researching /
        writing / awaiting_approval / completed). Drives the FastAPI
        `GET /research/{id}` endpoint in lesson 11.
    draft() -> str: the writer's draft, exposed once the workflow
        reaches the approval gate.
"""

from __future__ import annotations

from pydantic_ai.durable_exec.temporal import PydanticAIWorkflow
from temporalio import workflow

from agents.clarifier import clarifier
from agents.researcher import researcher
from agents.writer import writer


@workflow.defn
class ResearchWorkflow(PydanticAIWorkflow):
    """Three-agent research pipeline with HITL approval at the end."""

    # The plugin walks this list at worker startup and registers each
    # agent's auto-generated activities (model_request + every tool).
    __pydantic_ai_agents__ = [clarifier, researcher, writer]

    def __init__(self) -> None:
        # `__init__` runs on every workflow start AND on replay — that's
        # why signal-visible state lives here, not as class attributes.
        self._approved: bool = False
        self._approval_payload: str = ""
        self._draft: str = ""
        self._status: str = "starting"

    @workflow.signal
    def approve(self, payload: str = "") -> None:
        """Reviewer signal — flips the gate and stores the note.

        SYNC by Temporal convention: signal handlers mutate state and
        return; the workflow body reacts via `wait_condition`.
        """
        self._approval_payload = payload
        self._approved = True

    @workflow.query
    def draft(self) -> str:
        """Return the writer's draft (empty until the writer finishes)."""
        return self._draft

    @workflow.query
    def status(self) -> str:
        """Return the current pipeline stage."""
        return self._status

    @workflow.run
    async def run(self, topic: str) -> str:
        workflow.logger.info("ResearchWorkflow starting on topic=%s", topic)

        # Stage 1 — Clarifier narrows the topic into one question.
        self._status = "clarifying"
        clarified = await clarifier.run(
            f"Reformulate this topic into a single researchable question: {topic}"
        )

        # Stage 2 — Researcher answers using fake lookup tools.
        self._status = "researching"
        research = await researcher.run(clarified.output)

        # Stage 3 — Writer turns findings into a final report.
        self._status = "writing"
        drafted = await writer.run(
            f"Write a short report based on these findings: {research.output}"
        )
        self._draft = drafted.output

        # HITL gate — the durable pause. Costs nothing while waiting.
        self._status = "awaiting_approval"
        workflow.logger.info("Draft ready, awaiting approval signal...")
        await workflow.wait_condition(lambda: self._approved)
        workflow.logger.info("Approval received: %s", self._approval_payload)

        self._status = "completed"
        feedback = (
            f" [reviewer note: {self._approval_payload}]"
            if self._approval_payload
            else ""
        )
        return f"{drafted.output}{feedback}"
