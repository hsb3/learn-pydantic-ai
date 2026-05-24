"""Smoke test Lesson 09 under `WorkflowEnvironment.start_local()`.

Verifies that `LogfirePlugin` runs alongside `PydanticAIPlugin` and the
workflow still completes. We do NOT call `logfire.configure()` here —
`send_to_logfire="if-token-present"` is the production default, and
without a token Logfire is a clean no-op so the test runs anywhere.
"""

from __future__ import annotations

import pytest
from pydantic_ai.durable_exec.temporal import LogfirePlugin, PydanticAIPlugin
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from conftest import use_lesson

use_lesson("09_observability")

from learn_pydantic_ai import TASK_QUEUE  # noqa: E402
from learn_pydantic_ai.temporal import make_workflow_runner  # noqa: E402
from workflows import ResearchWorkflow  # noqa: E402


@pytest.mark.asyncio
async def test_lesson_09_runs() -> None:
    """Workflow runs to completion with `LogfirePlugin` in the plugin chain."""
    use_lesson("09_observability")
    # `PydanticAIPlugin` belongs on the client (start_local), `LogfirePlugin`
    # on the Worker — Logfire's plugin only implements `configure_worker`,
    # whereas PydanticAIPlugin's data-converter wiring is client-side.
    async with await WorkflowEnvironment.start_local(
        plugins=[PydanticAIPlugin()],
    ) as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[ResearchWorkflow],
            plugins=[LogfirePlugin()],
            workflow_runner=make_workflow_runner(),
        ):
            result = await env.client.execute_workflow(
                ResearchWorkflow.run,
                "How big is Tokyo and what currency does Japan use?",
                id="test-lesson-09",
                task_queue=TASK_QUEUE,
            )
            assert isinstance(result, str)
            assert len(result) > 0
