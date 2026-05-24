"""Lesson 07 — start the workflow, then auto-approve.

Run me in terminal B (with the worker from `worker.py` running):

    make temporal-07

The 3-second sleep is purely for demo purposes — it gives you a window to
watch the workflow show up in the UI in the `Running` state, suspended on
the `wait_condition`, before the signal arrives and unsticks it.

To do this manually instead — see the "Try it" section of the lesson doc.
"""

from __future__ import annotations

import asyncio
import uuid

from learn_pydantic_ai import TASK_QUEUE, connect
from workflows import ApprovalWorkflow


async def main() -> None:
    client = await connect()
    workflow_id = f"lesson-07-{uuid.uuid4().hex[:8]}"

    # `start_workflow` returns immediately with a handle; the workflow
    # keeps running on the worker. `execute_workflow` (which we used in
    # earlier lessons) would block until completion — useless here because
    # the workflow is going to suspend on `wait_condition` indefinitely.
    handle = await client.start_workflow(
        ApprovalWorkflow.run,
        "the joys of typed Python",
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    print(f"Workflow started: {workflow_id}")
    print(
        f"  UI: http://localhost:8080/namespaces/learn-pydantic-ai/workflows/{workflow_id}"
    )
    print("Auto-approving in 3s — open the UI now to see it paused...")
    await asyncio.sleep(3)

    # `handle.signal(...)` sends the signal by name. Passing the bound
    # method (`ApprovalWorkflow.approve`) lets the SDK derive the signal
    # name automatically — same as `.signal("approve", "...")` would.
    await handle.signal(ApprovalWorkflow.approve, "looks good, ship it")
    print("Signal sent. Waiting for workflow result...")

    result = await handle.result()
    print("\nResult:\n" + result)


if __name__ == "__main__":
    asyncio.run(main())
