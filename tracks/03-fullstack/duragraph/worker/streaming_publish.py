"""Publisher side of the streaming side channel (runs inside activities).

Workflows are deterministic and cannot do I/O; activities can. The model
activity (via the agent's event_stream_handler) publishes deltas here; the
API's SSE route subscribes (app/services/streaming.py). Keyed by run_id.

You already run managed Redis, so this is the path of least resistance.
Reference implementation: architectingbytes.com/posts/temporal-redis-sse.
"""
from __future__ import annotations

import json
from functools import lru_cache

import redis.asyncio as aioredis

from app.core.config import get_settings


@lru_cache
def _redis() -> aioredis.Redis:
    return aioredis.from_url(get_settings().redis_url, decode_responses=True)


def channel(run_id: str) -> str:
    return f"run:{run_id}"


async def publish_event(run_id: str, event: str, data: object) -> None:
    """event mirrors langgraph stream_mode names: values|messages|updates|events|interrupt|end|error."""
    await _redis().publish(channel(run_id), json.dumps({"event": event, "run_id": run_id, "data": data}, default=str))


async def publish_terminal(run_id: str, event: str, data: object) -> None:
    """Send a final marker so subscribers know to close the SSE connection."""
    await publish_event(run_id, event, data)
    await publish_event(run_id, "end", {"final_event": event})
