"""Lesson 11 capstone — custom long-running activity.

`fetch_external_context` simulates the kind of pre-research data fetch
you'd do in production — pulling user history, scraping a URL, hitting a
search API. The interesting part is the heartbeat: every second the
activity tells the Temporal cluster "I'm still alive," so the worker can
be killed mid-fetch and Temporal will reschedule the activity instead of
silently dropping the workflow.

This module is the **Lesson 08 contribution** to the capstone.

Dependencies:
    - temporalio: `@activity.defn` decorator + `activity.heartbeat`
"""

from __future__ import annotations

import asyncio

from temporalio import activity


@activity.defn
async def fetch_external_context(topic: str) -> str:
    """Simulate fetching pre-research context. Heartbeats every second.

    A real implementation would call out to a scraper, a vector DB, or a
    search API. Whatever it does, the rule from Lesson 08 holds: any
    activity whose `start_to_close_timeout` is bigger than ~10 seconds
    should heartbeat at a cadence smaller than its `heartbeat_timeout`.
    """
    activity.logger.info("fetch_external_context starting for topic=%s", topic)
    facts: list[str] = []
    for step in range(1, 6):
        activity.heartbeat(f"step {step}/5")
        await asyncio.sleep(1)
        facts.append(f"fact-{step}")
    activity.logger.info("fetch_external_context done")
    return f"Pre-fetched context for '{topic}': " + ", ".join(facts)
