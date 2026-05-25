"""Lesson 09 — kick off the researcher workflow.

Run me in terminal B (with the worker from `worker.py` already running):

    make temporal-09

I send one multi-step question. The agent will call BOTH tools to answer it,
so the resulting Temporal history has multiple model-request and tool
activities — and if `LOGFIRE_TOKEN` is set, the Logfire trace shows the same
tree with HTTP-level detail under each model request.
"""

from __future__ import annotations

import asyncio
import uuid

from learn_pydantic_ai import TASK_QUEUE, connect
from workflows import ResearchWorkflow


async def main() -> None:
    client = await connect()
    workflow_id = f"lesson-09-{uuid.uuid4().hex[:8]}"
    print(f"Starting workflow: {workflow_id}")

    result = await client.execute_workflow(
        ResearchWorkflow.run,
        "How big is Tokyo's population, and what currency does its country use?",
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    print("Result:", result)
    print(
        f"History: http://localhost:8080/namespaces/learn-pydantic-ai/workflows/{workflow_id}"
    )


if __name__ == "__main__":
    asyncio.run(main())
