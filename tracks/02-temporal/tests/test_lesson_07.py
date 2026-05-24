"""Smoke test Lesson 07 — start, signal, await.

Uses `WorkflowEnvironment.start_local()` so no docker stack is needed.
Starts the workflow, gives the worker a moment to draft, sends the
`approve` signal, then asserts the result reflects the approval.
"""

from __future__ import annotations

import asyncio

import pytest
from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from conftest import use_lesson

use_lesson("07_hitl_approval")

from learn_pydantic_ai import TASK_QUEUE  # noqa: E402
from learn_pydantic_ai.temporal import make_workflow_runner  # noqa: E402
from workflows import ApprovalWorkflow  # noqa: E402


@pytest.mark.asyncio
async def test_lesson_07_runs() -> None:
    """Workflow drafts, pauses on a signal, resumes, returns the payload."""
    use_lesson("07_hitl_approval")
    async with await WorkflowEnvironment.start_local(
        plugins=[PydanticAIPlugin()],
    ) as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[ApprovalWorkflow],
            workflow_runner=make_workflow_runner(),
        ):
            handle = await env.client.start_workflow(
                ApprovalWorkflow.run,
                "test topic",
                id="test-lesson-07",
                task_queue=TASK_QUEUE,
            )
            # Give the workflow a beat to do its draft + reach the
            # `wait_condition`. The signal would be queued by the server
            # against the workflow ID anyway, so this sleep is a comfort
            # margin, not a correctness gate.
            await asyncio.sleep(1)
            await handle.signal(ApprovalWorkflow.approve, "test approval")
            result = await handle.result()

            assert isinstance(result, str)
            assert "APPROVED" in result
            assert "test approval" in result
