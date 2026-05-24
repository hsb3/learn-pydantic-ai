"""Smoke test Lesson 08 — long-running activity with heartbeats.

Uses `WorkflowEnvironment.start_local()`. The worker registers the
custom `long_scrape` activity alongside `LongScrapeWorkflow` — same
shape the real `worker.py` uses.
"""

from __future__ import annotations

import pytest
from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from conftest import use_lesson

use_lesson("08_long_running")

from learn_pydantic_ai import TASK_QUEUE  # noqa: E402
from learn_pydantic_ai.temporal import make_workflow_runner  # noqa: E402
from scraper import long_scrape  # noqa: E402
from workflows import LongScrapeWorkflow  # noqa: E402


@pytest.mark.asyncio
async def test_lesson_08_runs() -> None:
    """Agent picks a URL, long activity heartbeats through its sleep, result returned."""
    use_lesson("08_long_running")
    async with await WorkflowEnvironment.start_local(
        plugins=[PydanticAIPlugin()],
    ) as env:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[LongScrapeWorkflow],
            activities=[long_scrape],
            workflow_runner=make_workflow_runner(),
        ):
            result = await env.client.execute_workflow(
                LongScrapeWorkflow.run,
                "Temporal durable execution basics",
                id="test-lesson-08",
                task_queue=TASK_QUEUE,
            )
            assert isinstance(result, str)
            assert "Topic:" in result
            assert "Result:" in result
            assert "scraped" in result
