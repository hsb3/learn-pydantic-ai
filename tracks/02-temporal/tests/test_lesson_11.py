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
