"""Lesson 02 — start the workflow, signal it, query it, await the result.

Run me in terminal B (worker must be up via `make temporal-02-worker`):

    make temporal-02

Unlike Lesson 01's `execute_workflow` (start + wait in one call), this
uses `start_workflow` so we hold a *handle*. A handle is what lets us
push signals in and read queries out while the workflow is still running
— the whole point of a stateful workflow.
"""

from __future__ import annotations

import asyncio
import uuid

from learn_pydantic_ai import TASK_QUEUE, connect
from workflows import TallyWorkflow


async def main() -> None:
    client = await connect()
    workflow_id = f"lesson-02-{uuid.uuid4().hex[:8]}"
    print(f"Starting workflow: {workflow_id} (target=10)")

    # `start_workflow` returns immediately with a handle — the workflow is
    # now running on the worker, paused inside `wait_condition`.
    handle = await client.start_workflow(
        TallyWorkflow.run,
        10,  # target
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )

    # Push values in via signals. Each `add` is recorded as an event in
    # workflow history and mutates `self._total` on the worker.
    for n in (3, 4):
        await handle.signal(TallyWorkflow.add, n)

    # Read the running total without stopping the workflow.
    running = await handle.query(TallyWorkflow.total)
    print(f"Running total after 3 + 4: {running}")  # 7 — still below target

    # One more push crosses the target (7 + 5 = 12), so `wait_condition`
    # releases and the run returns.
    await handle.signal(TallyWorkflow.add, 5)

    result = await handle.result()
    print(f"Final total (>= target, so the workflow returned): {result}")
    print(
        f"History: http://localhost:8080/namespaces/learn-pydantic-ai/workflows/{workflow_id}"
    )


if __name__ == "__main__":
    asyncio.run(main())
