"""Smoke test Lesson 02 under `WorkflowEnvironment.start_local()`.

The stateful plain workflow: start it, push values via `add` signals,
read the `total` query, and confirm `wait_condition` releases once the
tally crosses the target. No agent and no API calls — the fastest test
in the suite.
"""

from __future__ import annotations

import pytest
from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from conftest import use_lesson

use_lesson("02_stateful_workflow")

from learn_pydantic_ai import TASK_QUEUE  # noqa: E402
from learn_pydantic_ai.temporal import make_workflow_runner  # noqa: E402
from workflows import TallyWorkflow  # noqa: E402


@pytest.mark.asyncio
async def test_lesson_02_tally_releases_on_target() -> None:
    """Signals mutate state; the query reads it; wait_condition releases at target."""
    use_lesson("02_stateful_workflow")

    # `TallyWorkflow` itself uses no pydantic-ai, but `PydanticAIPlugin`
    # configures the sandbox passthroughs the suite relies on (pydantic_ai
    # pulls in a global beartype import hook). The real worker gets the
    # same plugin via `run_worker` -> `connect()`.
    async with await WorkflowEnvironment.start_local(
        plugins=[PydanticAIPlugin()],
    ) as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[TallyWorkflow],
            workflow_runner=make_workflow_runner(),
        ):
            handle = await env.client.start_workflow(
                TallyWorkflow.run,
                10,  # target
                id="test-lesson-02",
                task_queue=TASK_QUEUE,
            )

            await handle.signal(TallyWorkflow.add, 3)
            await handle.signal(TallyWorkflow.add, 4)
            # Query reads running state without ending the workflow.
            assert await handle.query(TallyWorkflow.total) == 7

            # Crossing the target releases wait_condition.
            await handle.signal(TallyWorkflow.add, 5)
            result = await handle.result()

    assert result == 12
