"""Lesson 08 — start the workflow and wait for the result.

Run me in terminal B (with the worker from `worker.py` running):

    make temporal-08

The total wall-clock time should be ~4–6 seconds: a fast LLM pick plus
the ~4-second simulated scrape. Open the UI while it's running and you
will see the `long_scrape` activity heartbeating every second.
"""

from __future__ import annotations

import asyncio
import uuid

from learn_pydantic_ai import TASK_QUEUE, connect
from workflows import LongScrapeWorkflow


async def main() -> None:
    client = await connect()
    workflow_id = f"lesson-08-{uuid.uuid4().hex[:8]}"
    print(f"Starting workflow: {workflow_id}")

    result = await client.execute_workflow(
        LongScrapeWorkflow.run,
        "Temporal durable execution basics",
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    print("\nResult:\n" + result)
    print(
        f"\nHistory: http://localhost:8080/namespaces/learn-pydantic-ai/workflows/{workflow_id}"
    )


if __name__ == "__main__":
    asyncio.run(main())
