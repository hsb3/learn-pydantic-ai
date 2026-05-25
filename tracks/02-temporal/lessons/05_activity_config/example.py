"""Lesson 05 — start one workflow and print the result.

This is the "client" side. The worker (`worker.py`) must already be running
in another terminal — or this call will block waiting for someone to pick
up the task.

The interesting bit isn't this script — it's the Temporal UI at
http://localhost:8080 after the run completes. Click into the workflow
you just started and inspect the history: you'll see the flaky tool
scheduled multiple times before it finally completes.
"""

from __future__ import annotations

import asyncio
import uuid

from learn_pydantic_ai import TASK_QUEUE, connect
from workflows import LookupWorkflow


async def main() -> None:
    client = await connect()
    workflow_id = f"lesson-05-{uuid.uuid4().hex[:8]}"
    result = await client.execute_workflow(
        LookupWorkflow.run,
        "Tell me about the Temporal SDK in one sentence.",
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    print(f"workflow_id: {workflow_id}")
    print(f"result: {result}")
    print(
        "\nOpen http://localhost:8080 and find this workflow under namespace "
        "`learn-pydantic-ai`. Watch the tool retry events."
    )


if __name__ == "__main__":
    asyncio.run(main())
