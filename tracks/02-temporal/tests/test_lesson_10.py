"""Smoke test the capstone end-to-end under WorkflowEnvironment.start_local().

Three real LLM round-trips (clarifier -> researcher -> writer) plus the
HITL approval signal. The test is the slowest in the suite because of
the chained model calls; expect ~15-30s wall clock.
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

use_lesson("10_capstone_headless")

from learn_pydantic_ai import TASK_QUEUE  # noqa: E402
from learn_pydantic_ai.temporal import make_workflow_runner  # noqa: E402
from workflow import ResearchWorkflow  # noqa: E402


@pytest.mark.asyncio
async def test_capstone_end_to_end() -> None:
    """Workflow runs all three agents, pauses, accepts approval, returns."""
    use_lesson("10_capstone_headless")

    # `plugins=[PydanticAIPlugin()]` goes on `start_local` (not the Worker)
    # so the client gets the PydanticPayloadConverter that knows how to
    # serialize the tagged-union types pydantic-ai uses internally for
    # tool returns. The worker inherits the plugin from its client.
    async with await WorkflowEnvironment.start_local(
        plugins=[PydanticAIPlugin()],
    ) as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[ResearchWorkflow],
            workflow_runner=make_workflow_runner(),
        ):
            handle = await env.client.start_workflow(
                ResearchWorkflow.run,
                "the population of Japan",
                id="test-capstone",
                task_queue=TASK_QUEUE,
            )

            # Wait long enough for clarify -> research -> write to land
            # and the workflow to enter `awaiting_approval`. Poll the
            # status query so the test doesn't depend on wall-clock luck.
            for _ in range(60):
                await asyncio.sleep(1)
                # Catch only the query-not-yet-ready failures, not arbitrary
                # exceptions — a real bug here should propagate, not silently
                # extend the poll loop.
                try:
                    status = await handle.query(ResearchWorkflow.status)
                except (WorkflowQueryFailedError, RPCError):
                    status = "starting"
                if status == "awaiting_approval":
                    break
            else:
                pytest.fail("workflow never reached awaiting_approval")

            await handle.signal(ResearchWorkflow.approve, "looks good")
            result = await asyncio.wait_for(handle.result(), timeout=60)

    assert isinstance(result, str)
    assert len(result) > 0
    # Approval note rides on the final string.
    assert "looks good" in result
