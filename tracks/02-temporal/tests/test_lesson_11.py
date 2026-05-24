"""Smoke test the FastAPI capstone workflow under WorkflowEnvironment.start_local().

Exercises `CapstoneWorkflow` directly (not the FastAPI layer): the
long-running `fetch_external_context` activity, three chained agent runs
(clarifier -> researcher -> writer), and the HITL approval signal. The
HTTP surface in `app.py` is a thin wrapper over these same primitives,
so testing the workflow covers the durable behavior that matters.

Slowest test in the suite — chained model calls plus the simulated
pre-fetch run ~20-40s wall clock.
"""

from __future__ import annotations

import asyncio

import pytest
from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from temporalio.client import WorkflowQueryFailedError
from temporalio.service import RPCError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from conftest import use_lesson

use_lesson("11_capstone_fastapi")

from activities import fetch_external_context  # noqa: E402
from learn_pydantic_ai import TASK_QUEUE  # noqa: E402
from learn_pydantic_ai.temporal import make_workflow_runner  # noqa: E402
from workflow import CapstoneWorkflow  # noqa: E402


@pytest.mark.asyncio
async def test_capstone_fastapi_workflow_end_to_end() -> None:
    """Pre-fetch + three agents + HITL gate run end-to-end and return the report."""
    use_lesson("11_capstone_fastapi")

    # `plugins=[PydanticAIPlugin()]` goes on `start_local` (the client) so
    # the PydanticPayloadConverter is installed; the Worker inherits it.
    # `fetch_external_context` is a custom @activity.defn, so it must be
    # registered explicitly — only the agents' activities are auto-registered.
    async with await WorkflowEnvironment.start_local(
        plugins=[PydanticAIPlugin()],
    ) as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[CapstoneWorkflow],
            activities=[fetch_external_context],
            workflow_runner=make_workflow_runner(),
        ):
            handle = await env.client.start_workflow(
                CapstoneWorkflow.run,
                "the population of Japan",
                id="test-capstone-fastapi",
                task_queue=TASK_QUEUE,
            )

            # Poll the status query until the pipeline reaches the HITL gate.
            # Catch only the query-not-yet-ready failures so a real bug
            # propagates instead of silently extending the loop.
            for _ in range(90):
                await asyncio.sleep(1)
                try:
                    status = await handle.query(CapstoneWorkflow.status)
                except (WorkflowQueryFailedError, RPCError):
                    status = "starting"
                if status == "awaiting_approval":
                    break
            else:
                pytest.fail("workflow never reached awaiting_approval")

            await handle.signal(CapstoneWorkflow.approve, "looks good")
            result = await asyncio.wait_for(handle.result(), timeout=60)

    assert isinstance(result, str)
    assert len(result) > 0
    # Approval note rides on the final string.
    assert "looks good" in result


async def _status(handle) -> str:
    """Query the live status, treating not-yet-ready queries as 'starting'."""
    try:
        return await handle.query(CapstoneWorkflow.status)
    except (WorkflowQueryFailedError, RPCError):
        return "starting"


async def _wait_for_gate(handle, *, timeout: int = 180) -> None:
    """Poll until the workflow parks at the HITL gate."""
    for _ in range(timeout):
        if await _status(handle) == "awaiting_approval":
            return
        await asyncio.sleep(1)
    pytest.fail("workflow never reached awaiting_approval")


@pytest.mark.asyncio
async def test_capstone_revise_loops_back_then_approves() -> None:
    """A `revise` signal sends the draft back to the writer and returns to the gate."""
    use_lesson("11_capstone_fastapi")

    async with await WorkflowEnvironment.start_local(
        plugins=[PydanticAIPlugin()],
    ) as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[CapstoneWorkflow],
            activities=[fetch_external_context],
            workflow_runner=make_workflow_runner(),
        ):
            handle = await env.client.start_workflow(
                CapstoneWorkflow.run,
                "the population of Japan",
                id="test-capstone-revise",
                task_queue=TASK_QUEUE,
            )

            await _wait_for_gate(handle)
            draft_before = await handle.query(CapstoneWorkflow.draft)
            assert draft_before  # writer produced a first draft

            # Force a clearly different draft, then wait until the workflow
            # loops back to the gate with the new text. This proves `revise`
            # re-ran the writer rather than terminating the run.
            await handle.signal(
                CapstoneWorkflow.revise,
                "Rewrite the entire report as exactly three short bullet points.",
            )
            draft_after = draft_before
            for _ in range(180):
                if (
                    await _status(handle) == "awaiting_approval"
                    and (draft_after := await handle.query(CapstoneWorkflow.draft))
                    != draft_before
                ):
                    break
                await asyncio.sleep(1)
            else:
                pytest.fail("revise never produced a new draft back at the gate")

            assert draft_after and draft_after != draft_before

            # Approving after a revision still finishes normally.
            await handle.signal(CapstoneWorkflow.approve, "lgtm")
            result = await asyncio.wait_for(handle.result(), timeout=60)

    assert isinstance(result, str)
    assert "lgtm" in result


@pytest.mark.asyncio
async def test_capstone_reject_closes_without_shipping() -> None:
    """A `reject` signal ends the run without shipping, recording the reason."""
    use_lesson("11_capstone_fastapi")

    async with await WorkflowEnvironment.start_local(
        plugins=[PydanticAIPlugin()],
    ) as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[CapstoneWorkflow],
            activities=[fetch_external_context],
            workflow_runner=make_workflow_runner(),
        ):
            handle = await env.client.start_workflow(
                CapstoneWorkflow.run,
                "the GDP of Germany",
                id="test-capstone-reject",
                task_queue=TASK_QUEUE,
            )

            await _wait_for_gate(handle)
            await handle.signal(CapstoneWorkflow.reject, "out of scope for this demo")
            result = await asyncio.wait_for(handle.result(), timeout=60)

    assert result.startswith("REJECTED")
    assert "out of scope for this demo" in result
