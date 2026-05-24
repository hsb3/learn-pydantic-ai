"""Smoke test Lesson 06 under `WorkflowEnvironment.start_local()`.

Verifies that running the workflow produces a non-empty answer AND that
the event_stream_handler fired at least once for several event kinds.
"""

from __future__ import annotations

import pytest
from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from conftest import use_lesson

use_lesson("06_streaming")

from learn_pydantic_ai import TASK_QUEUE  # noqa: E402
from learn_pydantic_ai.temporal import make_workflow_runner  # noqa: E402
from workflows import StreamingWorkflow, event_counts  # noqa: E402


@pytest.mark.asyncio
async def test_lesson_06_streams_events() -> None:
    """Workflow completes AND the handler observed stream events."""
    use_lesson("06_streaming")
    event_counts.clear()

    async with await WorkflowEnvironment.start_local(
        plugins=[PydanticAIPlugin()],
    ) as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[StreamingWorkflow],
            workflow_runner=make_workflow_runner(),
        ):
            result = await env.client.execute_workflow(
                StreamingWorkflow.run,
                "Please double 21 for me.",
                id="test-lesson-06",
                task_queue=TASK_QUEUE,
            )

    assert isinstance(result, str)
    assert len(result) > 0
    # Some events MUST have streamed through the handler. The exact mix
    # depends on the model — but `part_start` should always show up for a
    # successful run.
    assert sum(event_counts.values()) > 0, "handler never observed any events"
    assert event_counts.get("part_start", 0) > 0
