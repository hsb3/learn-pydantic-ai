"""Lesson 05 — worker process.

Long-running. Polls the shared `learn-pydantic-ai` task queue. Picks up
`LookupWorkflow` invocations and runs the agent + tool activities — including
all the retries that make this lesson worth watching.

Run with:
    make temporal-05-worker
"""

from __future__ import annotations

import asyncio
import logging

from learn_pydantic_ai import run_worker
from workflows import LookupWorkflow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
)


async def main() -> None:
    await run_worker(workflows=[LookupWorkflow])


if __name__ == "__main__":
    asyncio.run(main())
