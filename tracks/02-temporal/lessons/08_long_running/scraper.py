"""Lesson 08 — the long-running activity.

This is a plain `@activity.defn` (not a pydantic-ai tool). It lives in its
own module so the worker can register it explicitly via the
`activities=[long_scrape]` kwarg to `run_worker`.

Why not make it a pydantic-ai `@agent.tool_plain`? You can — pydantic-ai
lifts every tool call into its own activity via `TemporalAgent`, so
calling `activity.heartbeat()` from inside a tool body technically works.
But that ties the long-running work to a model call, which is wasteful
(every retry of the activity would also re-run the LLM). Keeping the slow
side-effecting work as its own activity invoked directly from the
workflow body lets the agent and the long work retry independently — the
durable pattern you'd actually ship.
"""

from __future__ import annotations

import asyncio

from temporalio import activity


@activity.defn
async def long_scrape(url: str) -> str:
    """Simulate a 4-second scrape. Heartbeats every second so Temporal
    knows we're alive even though we haven't returned anything yet.

    In a real activity this body would call `httpx.get()` or kick off a
    Playwright session; the side-effecting call is what makes it activity
    code and not workflow code.
    """
    activity.logger.info("long_scrape starting url=%s", url)

    total_seconds = 4
    for i in range(total_seconds):
        await asyncio.sleep(1)
        # `activity.heartbeat(...)` is the "I'm still alive" ping. Without
        # it, Temporal would consider this activity dead once
        # `heartbeat_timeout` elapses with no contact, and would re-schedule
        # the whole activity on another worker. The optional positional
        # arg is "details" — anything pickleable that's preserved across
        # restarts via `activity.heartbeat_details()` for resume logic.
        activity.heartbeat(f"chunk {i + 1}/{total_seconds}")
        activity.logger.info("long_scrape heartbeat %d/%d", i + 1, total_seconds)

    return f"[scraped {url}: lorem ipsum dolor sit amet]"
