"""Lesson 08 — worker process.

Run me in terminal A:

    make temporal-08-worker

This is the first lesson where the worker registers a **custom activity**
alongside its workflow. `long_scrape` lives in `scraper.py` as a plain
`@activity.defn`; we pass it via `activities=[long_scrape]` so the worker
will pick up activity tasks for it from the task queue. PydanticAI's
auto-generated activities (model calls, tool calls) are still installed
by `PydanticAIPlugin` — no change there.
"""

from __future__ import annotations

import asyncio
import logging

from learn_pydantic_ai import run_worker
from scraper import long_scrape
from workflows import LongScrapeWorkflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


async def main() -> None:
    await run_worker(workflows=[LongScrapeWorkflow], activities=[long_scrape])


if __name__ == "__main__":
    asyncio.run(main())
