"""Lesson 11 capstone — durable research workflow that pulls in every track concept.

Pipeline:

    1. `fetch_external_context` long-running activity      (Lesson 08)
    2. Clarifier agent run with retry config                (Lessons 03, 05)
    3. Researcher agent: tools + per-tool config + streaming (Lessons 04, 05, 06)
    4. Writer agent                                          (Lesson 10 pattern)
    5. Workflow pauses for signal (HITL)                     (Lesson 07)
    6. Returns final report

Concepts mapped to lesson sources:

    | Concept                                | Lesson |
    |---|---|
    | `TemporalAgent` + `PydanticAIWorkflow` | 02     |
    | `@agent.tool_plain` lifted to activity | 03     |
    | `activity_config` + `tool_activity_config` retry tiers | 04     |
    | `event_stream_handler` streams events  | 05     |
    | `@workflow.signal` + `workflow.wait_condition` | 06     |
    | `workflow.execute_activity` + heartbeats | 07     |
    | `LogfirePlugin` observability (wired in `worker.py`) | 08     |
    | Multi-agent orchestration               | 09     |

The worker process attaches `LogfirePlugin` so every activity in this
workflow is a Logfire span with full HTTP-level capture.
"""

from __future__ import annotations

from datetime import timedelta

from pydantic_ai.durable_exec.temporal import PydanticAIWorkflow
from temporalio import workflow

from activities import fetch_external_context
from agents import clarifier, researcher, writer


@workflow.defn
class CapstoneWorkflow(PydanticAIWorkflow):
    """The graduation workflow — every concept from the track in one durable run."""

    # PydanticAIPlugin walks this list at worker startup and registers each
    # agent's auto-generated model + tool activities.
    __pydantic_ai_agents__ = [clarifier, researcher, writer]

    def __init__(self) -> None:
        # Lesson 07 — per-instance state for the HITL gate. Exactly one of the
        # review signals sets `_decision`; the run loop waits on it.
        self._decision: str | None = None  # "approve" | "revise" | "reject"
        self._feedback: str = ""  # revise instructions or reject reason
        self._approval_note: str = ""
        # Lesson 10 — live status / draft exposed via queries.
        self._status: str = "starting"
        self._draft: str = ""

    @workflow.signal
    def approve(self, note: str = "") -> None:
        """Approve the current draft and finish. Signal handlers MUST be sync."""
        self._approval_note = note
        self._decision = "approve"

    @workflow.signal
    def revise(self, feedback: str) -> None:
        """Send the draft back to the writer with feedback, then re-review."""
        self._feedback = feedback
        self._decision = "revise"

    @workflow.signal
    def reject(self, reason: str = "") -> None:
        """Reject the draft; the run ends without shipping."""
        self._feedback = reason
        self._decision = "reject"

    @workflow.query
    def status(self) -> str:
        """Live pipeline stage. Queryable from the FastAPI layer."""
        return self._status

    @workflow.query
    def draft(self) -> str:
        """Latest draft text. Exposed to reviewers before they approve."""
        return self._draft

    @workflow.run
    async def run(self, topic: str) -> str:
        workflow.logger.info("CapstoneWorkflow starting for topic=%s", topic)

        # ── Stage 1 — Lesson 08: long-running pre-fetch ────────────────────
        self._status = "fetching_context"
        context = await workflow.execute_activity(
            fetch_external_context,
            topic,
            start_to_close_timeout=timedelta(minutes=2),
            heartbeat_timeout=timedelta(seconds=10),
        )

        # ── Stage 2 — Lessons 03, 05: clarifier with retry config ──────────
        self._status = "clarifying"
        clarified = await clarifier.run(
            f"Topic: {topic}\nContext: {context}\n\n"
            "Narrow this into one focused researchable question."
        )

        # ── Stage 3 — Lessons 04, 05, 06: researcher with tools + streaming ─
        self._status = "researching"
        research = await researcher.run(clarified.output)

        # ── Stage 4 — writer turns findings into a draft report ────────────
        self._status = "writing"
        drafted = await writer.run(
            f"Question: {clarified.output}\nFindings: {research.output}\n\n"
            "Write the report."
        )
        self._draft = drafted.output

        # ── Stage 5 — Lesson 07: HITL gate, now approve / revise / reject ───
        # A loop so "revise" can send the draft back to the writer and return
        # to the gate. The loop exits only on approve or reject.
        while True:
            self._decision = None
            self._status = "awaiting_approval"
            workflow.logger.info("Draft ready, awaiting review decision")
            await workflow.wait_condition(lambda: self._decision is not None)

            if self._decision == "approve":
                self._status = "completed"
                note = (
                    f"\n\n--- Reviewer note: {self._approval_note}"
                    if self._approval_note
                    else ""
                )
                return self._draft + note

            if self._decision == "reject":
                self._status = "rejected"
                reason = f"\n\nReason: {self._feedback}" if self._feedback else ""
                return f"REJECTED — the reviewer closed this without shipping.{reason}"

            # "revise" — fold the feedback back into the writer, then re-review.
            self._status = "revising"
            workflow.logger.info("Revision requested: %s", self._feedback)
            redrafted = await writer.run(
                f"Question: {clarified.output}\nFindings: {research.output}\n\n"
                f"Current draft:\n{self._draft}\n\n"
                f"Revise the draft to address this reviewer feedback:\n"
                f"{self._feedback}\n\nReturn the full revised report."
            )
            self._draft = redrafted.output
