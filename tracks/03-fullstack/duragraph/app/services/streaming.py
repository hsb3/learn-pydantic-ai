"""Subscriber side of the streaming side channel: Redis pub/sub -> SSE.

Two-step on purpose: open_subscription() is awaited (subscription is live)
BEFORE the route signals the run, so early deltas aren't lost. pub/sub still
has a tiny pre-subscribe race and no replay; for resumable streams (refresh
mid-response) upgrade to Redis Streams (XADD/XREAD + Last-Event-ID). See
zknill.io on why "resumable + cancellable + multi-device" is the hard part.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import redis.asyncio as aioredis

from app.core.config import get_settings


async def open_subscription(run_id: str):
    r = aioredis.from_url(get_settings().redis_url, decode_responses=True)
    ps = r.pubsub()
    await ps.subscribe(f"run:{run_id}")
    return r, ps


async def iter_events(
    r, ps, run_id: str, idle_timeout: float = 120.0
) -> AsyncIterator[dict]:
    try:
        while True:
            # NOTE: do NOT pass ignore_subscribe_messages=True. With that flag,
            # the first get_message() consumes the buffered subscribe-confirmation
            # and returns None *immediately* — which we'd misread as an idle
            # timeout and break before the first real event ever arrives. Instead
            # we keep subscribe/unsubscribe frames visible and skip them by type,
            # so a None return unambiguously means "idle_timeout elapsed".
            msg = await ps.get_message(timeout=idle_timeout)
            if msg is None:
                break  # genuine idle timeout — stop streaming
            if msg.get("type") != "message":
                continue  # subscribe/unsubscribe confirmation
            payload = json.loads(msg["data"])
            # sse-starlette envelope
            yield {"event": payload["event"], "data": json.dumps(payload["data"])}
            if payload["event"] in ("end", "error"):
                break
    finally:
        await ps.unsubscribe(f"run:{run_id}")
        await ps.aclose()
        await r.aclose()
