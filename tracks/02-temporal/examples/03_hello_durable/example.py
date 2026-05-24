"""Lesson 03 — kick off the workflow.

Run me in terminal B (with the worker from `worker.py` already running):

    make temporal-03

I connect to the same Temporal server the worker is polling, start one
`HelloWorkflow` execution, wait for the result, and print it. Then open
http://localhost:8080, find the workflow ID printed below, and inspect
its history to see the model-request activity in the timeline.
"""

from __future__ import annotations

import asyncio
import uuid

from learn_pydantic_ai import TASK_QUEUE, connect
from workflows import HelloWorkflow


async def main() -> None:
    client = await connect()
    workflow_id = f"lesson-03-{uuid.uuid4().hex[:8]}"
    print(f"Starting workflow: {workflow_id}")

    # `execute_workflow` = start + wait. For fire-and-forget, use
    # `start_workflow` and call `.result()` on the returned handle later.
    result = await client.execute_workflow(
        HelloWorkflow.run,
        "Where does 'hello world' come from?",
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    print("Result:", result)
    print(
        f"History: http://localhost:8080/namespaces/learn-pydantic-ai/workflows/{workflow_id}"
    )


if __name__ == "__main__":
    asyncio.run(main())
