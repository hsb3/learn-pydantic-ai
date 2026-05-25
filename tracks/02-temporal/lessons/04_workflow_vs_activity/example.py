"""Lesson 04 — kick off the workflow + point you at the history view.

Run me in terminal B (with the worker running):

    make temporal-04

After it prints `Result: ...`, open the printed URL. The history panel
should show, in order:

    ActivityTaskScheduled / ActivityTaskCompleted  -- model_request (#1)
    ActivityTaskScheduled / ActivityTaskCompleted  -- get_weather
    ActivityTaskScheduled / ActivityTaskCompleted  -- model_request (#2)
    WorkflowExecutionCompleted

That is the workflow-vs-activity boundary made visible.
"""

from __future__ import annotations

import asyncio
import uuid

from learn_pydantic_ai import TASK_QUEUE, connect
from workflows import WeatherWorkflow


async def main() -> None:
    client = await connect()
    workflow_id = f"lesson-04-{uuid.uuid4().hex[:8]}"
    print(f"Starting workflow: {workflow_id}")

    result = await client.execute_workflow(
        WeatherWorkflow.run,
        "London",
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    print("Result:", result)
    print(
        "History: "
        f"http://localhost:8080/namespaces/learn-pydantic-ai/workflows/{workflow_id}"
    )


if __name__ == "__main__":
    asyncio.run(main())
