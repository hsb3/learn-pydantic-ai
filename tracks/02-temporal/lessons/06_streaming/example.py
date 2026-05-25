"""Lesson 06 — start one workflow and print the final answer.

The interesting stream output appears in the **worker's** terminal (see
`worker.py`'s `log_events` handler). This script just kicks off the run
and prints the agent's final string.
"""

from __future__ import annotations

import asyncio
import uuid

from learn_pydantic_ai import TASK_QUEUE, connect
from workflows import StreamingWorkflow


async def main() -> None:
    client = await connect()
    workflow_id = f"lesson-06-{uuid.uuid4().hex[:8]}"
    result = await client.execute_workflow(
        StreamingWorkflow.run,
        "Please double 21 for me.",
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    print(f"workflow_id: {workflow_id}")
    print(f"final answer: {result}")
    print(
        "\nLook in the worker terminal for the [event] ... lines logged by "
        "the event_stream_handler. The Temporal UI will show the "
        "handler activities under workflow_id above."
    )


if __name__ == "__main__":
    asyncio.run(main())
