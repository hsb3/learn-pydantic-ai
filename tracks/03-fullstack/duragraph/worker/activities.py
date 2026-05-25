"""Activities the workflow uses for I/O it cannot do itself (publishing
stream events to Redis). Pydantic AI tool calls and model requests become
activities automatically under TemporalAgent, so they do not appear here.
"""
from __future__ import annotations

from typing import Any

from temporalio import activity

from worker.streaming_publish import publish_event, publish_terminal


@activity.defn
async def publish_activity(run_id: str, event: str, data: Any) -> None:
    await publish_event(run_id, event, data)


@activity.defn
async def publish_terminal_activity(run_id: str, event: str, data: Any) -> None:
    await publish_terminal(run_id, event, data)


ALL_ACTIVITIES = [publish_activity, publish_terminal_activity]
