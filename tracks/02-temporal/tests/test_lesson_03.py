"""Smoke test Lesson 03 under `WorkflowEnvironment.start_local()`.

Spins up an in-process Temporal server, registers the lesson's workflow,
starts one execution end-to-end, and asserts a non-empty string came back.
No docker stack required — `start_local()` downloads + runs a real
Temporal server binary in a subprocess and tears it down on exit.
"""

from __future__ import annotations

import pytest
from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from conftest import use_lesson

use_lesson("03_hello_durable")

from learn_pydantic_ai import TASK_QUEUE  # noqa: E402
from learn_pydantic_ai.temporal import make_workflow_runner  # noqa: E402
from workflows import HelloWorkflow  # noqa: E402


@pytest.mark.asyncio
async def test_lesson_03_runs() -> None:
    """The workflow returns a non-empty string."""
    # Re-pin sys.path inside the test — sibling test modules' own
    # `use_lesson()` calls (run at collection time) may have left a
    # different lesson dir at sys.path[0]. The Temporal workflow sandbox
    # imports `workflows` by name at Worker validation, and it needs
    # *this* lesson's file.
    use_lesson("03_hello_durable")

    # `PydanticAIPlugin` goes on `start_local` (the client side) — that's
    # what installs `PydanticPayloadConverter`. The Worker inherits the
    # plugin from its client. Passing it on the Worker too would
    # double-register `__pydantic_ai_agents__` activities and crash startup.
    async with await WorkflowEnvironment.start_local(
        plugins=[PydanticAIPlugin()],
    ) as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[HelloWorkflow],
            workflow_runner=make_workflow_runner(),
        ):
            result = await env.client.execute_workflow(
                HelloWorkflow.run,
                "Say hi.",
                id="test-lesson-03",
                task_queue=TASK_QUEUE,
            )
            assert isinstance(result, str)
            assert len(result) > 0
