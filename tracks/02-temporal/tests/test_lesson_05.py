"""Smoke test Lesson 05 under `WorkflowEnvironment.start_local()`.

Verifies that the retry policy rides out FAIL_FIRST_N transient errors
and the agent ultimately produces a non-empty string answer.
"""

from __future__ import annotations

import importlib

import pytest
from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from conftest import use_lesson

use_lesson("05_activity_config")

from learn_pydantic_ai import TASK_QUEUE  # noqa: E402
from learn_pydantic_ai.temporal import make_workflow_runner  # noqa: E402

flaky_tool = importlib.import_module("flaky_tool")  # noqa: E402
from workflows import LookupWorkflow  # noqa: E402


@pytest.mark.asyncio
async def test_lesson_05_retries_until_success() -> None:
    """Workflow rides out FAIL_FIRST_N transient errors and completes."""
    use_lesson("05_activity_config")
    # Reset module-level counter so re-runs are deterministic.
    flaky_tool.reset_counter()

    async with await WorkflowEnvironment.start_local(
        plugins=[PydanticAIPlugin()],
    ) as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[LookupWorkflow],
            workflow_runner=make_workflow_runner(),
        ):
            result = await env.client.execute_workflow(
                LookupWorkflow.run,
                "Tell me about the Temporal SDK in one sentence.",
                id="test-lesson-05",
                task_queue=TASK_QUEUE,
            )

    # Tool succeeds on attempt FAIL_FIRST_N + 1 = 3. The model summarises
    # its return value into a natural-language answer, so we can't pin to
    # the exact string — just assert the run completed and the counter
    # crossed the failure threshold.
    assert isinstance(result, str)
    assert len(result) > 0
    assert flaky_tool._attempts >= flaky_tool.FAIL_FIRST_N + 1
