"""Lesson 07 — pause a workflow until a human (or another process) approves.

The shape:

1. The workflow drafts something with a pydantic-ai agent (just like
   Lesson 04/04). The draft is stored on `self._draft` so it's readable
   via a `@workflow.query` while the workflow is paused.
2. It then calls `workflow.wait_condition(lambda: self._approved)` and the
   coroutine suspends — durably. The worker can crash, restart, or take a
   weeklong vacation; the workflow resumes exactly where it paused once a
   signal arrives.
3. The `@workflow.signal approve(...)` method writes to instance state.
   The `wait_condition` predicate re-evaluates on the next workflow task,
   sees `_approved == True`, and the workflow body continues.

Signals (write) and queries (read) are the two halves of the workflow's
external interface. Signals mutate, queries observe — both served by the
workflow class itself, both gRPC calls dispatched by the cluster.

This is the durable analogue of LangGraph's `interrupt()` — but instead
of a checkpointer storing a paused thread, Temporal stores the whole
workflow history server-side.
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import PydanticAIWorkflow, TemporalAgent
from temporalio import workflow

from learn_pydantic_ai import FLASH

# CRITICAL: `name=` is required on every Agent wrapped by TemporalAgent.
_base = Agent(
    model=FLASH,
    name="draft_agent",
    instructions=(
        "You draft short, one-paragraph blurbs on a given topic. "
        "Keep it under 60 words."
    ),
)
draft_agent = TemporalAgent(_base)


@workflow.defn
class ApprovalWorkflow(PydanticAIWorkflow):
    """Draft → pause → approve → return."""

    __pydantic_ai_agents__ = [draft_agent]

    def __init__(self) -> None:
        # `__init__` IS called every time the workflow starts (or replays
        # from history). Putting mutable state on `self` is the standard
        # signal/query pattern.
        self._draft: str | None = None
        self._approved: bool = False
        self._approval_payload: str | None = None

    @workflow.signal
    def approve(self, payload: str) -> None:
        """Send the approval. SYNC (no `async`) by Temporal convention —
        signal handlers shouldn't suspend on activities; they just mutate
        state and let the workflow body react via `wait_condition`."""
        self._approval_payload = payload
        self._approved = True

    @workflow.query
    def current_draft(self) -> str | None:
        """Read the current draft without affecting workflow state.

        Queries are the read-side counterpart to signals: signals MUTATE
        instance state, queries OBSERVE it. Both are gRPC calls served by
        the workflow class; queries must be deterministic and side-effect
        free, hence SYNC (no `async`) and no `await`s."""
        return self._draft

    @workflow.run
    async def run(self, topic: str) -> str:
        workflow.logger.info("ApprovalWorkflow drafting on topic=%s", topic)
        draft = await draft_agent.run(f"Draft a short blurb about: {topic}")
        # Expose the draft to query callers BEFORE we suspend on
        # wait_condition. A reviewer using the UI or CLI can now read the
        # draft via `current_draft` while deciding whether to approve.
        self._draft = draft.output

        workflow.logger.info("Draft ready, waiting for approval signal...")
        # The durable pause. Equivalent to `await event.wait()`, except the
        # condition predicate is re-evaluated on every workflow task — so
        # the wake-up trigger is any state mutation by a signal handler.
        await workflow.wait_condition(lambda: self._approved)
        workflow.logger.info("Approval received: %s", self._approval_payload)

        return (
            f"APPROVED — feedback: {self._approval_payload}\n\n"
            f"Original draft:\n{self._draft}"
        )
