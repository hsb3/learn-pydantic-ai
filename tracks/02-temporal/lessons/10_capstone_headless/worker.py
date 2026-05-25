"""Lesson 10 — capstone worker.

Same shape as every other lesson's worker: one workflow to register
(`ResearchWorkflow`), which itself declares three TemporalAgents via
`__pydantic_ai_agents__`. The plugin handles the rest at startup.

Run me in terminal A:

    make temporal-10-worker
"""

from __future__ import annotations

import asyncio
import logging

from learn_pydantic_ai import run_worker
from workflow import ResearchWorkflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


async def main() -> None:
    await run_worker(workflows=[ResearchWorkflow])


if __name__ == "__main__":
    asyncio.run(main())
