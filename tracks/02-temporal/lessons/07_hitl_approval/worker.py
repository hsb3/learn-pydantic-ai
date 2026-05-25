"""Lesson 07 — worker process.

Run me in terminal A:

    make temporal-07-worker

Same shape as every other lesson's worker — I just register a workflow
that happens to have a `@workflow.signal` handler. Workers don't need to
know about signals; the server routes them to whichever worker picks up
the matching workflow task.
"""

from __future__ import annotations

import asyncio
import logging

from learn_pydantic_ai import run_worker
from workflows import ApprovalWorkflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


async def main() -> None:
    await run_worker(workflows=[ApprovalWorkflow])


if __name__ == "__main__":
    asyncio.run(main())
