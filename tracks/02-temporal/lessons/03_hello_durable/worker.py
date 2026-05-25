"""Lesson 03 — worker process.

Run me in terminal A:

    make temporal-03-worker

I poll the `learn-pydantic-ai` task queue forever. Press Ctrl-C to stop.

`run_worker` (from `learn_pydantic_ai.temporal`) does the heavy lifting:
connects to the Temporal server, installs the PydanticAIPlugin, configures
the sandboxed workflow runner with our package as a passthrough, and blocks
on SIGINT/SIGTERM. All this worker has to do is hand it the workflow list.
"""

from __future__ import annotations

import asyncio
import logging

from learn_pydantic_ai import run_worker
from workflows import HelloWorkflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


async def main() -> None:
    await run_worker(workflows=[HelloWorkflow])


if __name__ == "__main__":
    asyncio.run(main())
