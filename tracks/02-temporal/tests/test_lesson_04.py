"""Smoke test Lesson 04 under `WorkflowEnvironment.start_local()`.

Same shape as `test_lesson_03.py`, but the workflow under test has one
`@agent.tool_plain` registered. We don't pass `activities=[...]`
manually — `PydanticAIPlugin` walks `__pydantic_ai_agents__` and
auto-discovers the tool's activity. If the wiring is wrong, the worker
either rejects the workflow at startup or the workflow hangs waiting for
an activity nobody is running.
"""

from __future__ import annotations

import pytest
from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from conftest import use_lesson

use_lesson("04_workflow_vs_activity")

from learn_pydantic_ai import TASK_QUEUE  # noqa: E402
from learn_pydantic_ai.temporal import make_workflow_runner  # noqa: E402
from workflows import WeatherWorkflow  # noqa: E402


@pytest.mark.asyncio
async def test_lesson_04_runs() -> None:
    """Workflow returns a non-empty string after invoking the weather tool."""
    use_lesson("04_workflow_vs_activity")
    async with await WorkflowEnvironment.start_local(
        plugins=[PydanticAIPlugin()],
    ) as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[WeatherWorkflow],
            workflow_runner=make_workflow_runner(),
        ):
            result = await env.client.execute_workflow(
                WeatherWorkflow.run,
                "London",
                id="test-lesson-04",
                task_queue=TASK_QUEUE,
            )
            assert isinstance(result, str)
            assert len(result) > 0
