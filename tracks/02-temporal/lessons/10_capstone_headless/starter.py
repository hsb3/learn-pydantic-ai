"""Lesson 10 — kick off the capstone workflow and auto-approve.

Run me in terminal B (worker must be up via `make temporal-10-worker`):

    make temporal-10

The 5-second sleep gives you a window to open the workflow in the
Temporal UI and watch it transition through `clarifying` ->
`researching` -> `writing` -> `awaiting_approval`. You can also poll
the status query manually with `temporal workflow query --type status`.
"""

from __future__ import annotations

import asyncio
import uuid

from learn_pydantic_ai import TASK_QUEUE, connect
from workflow import ResearchWorkflow


async def main() -> None:
    client = await connect()
    workflow_id = f"research-{uuid.uuid4().hex[:8]}"

    handle = await client.start_workflow(
        ResearchWorkflow.run,
        "the economy of Japan",
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    print(f"Started workflow {workflow_id}")
    print(
        f"  UI: http://localhost:8080/namespaces/learn-pydantic-ai/workflows/{workflow_id}"
    )
    print("Auto-approving in 5s — open the UI now to watch it pause...")
    await asyncio.sleep(5)

    print("Sending approval signal...")
    await handle.signal(ResearchWorkflow.approve, "looks good, ship it")

    result = await handle.result()
    print("\nFinal report:\n")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
