"""Lesson 06 — worker process.

This worker prints every (non-delta) AgentStreamEvent to stdout as the
workflow runs. Keep this terminal visible while running the starter from
another terminal — that's where the streaming output appears.

Run with:
    make temporal-06-worker
"""

from __future__ import annotations

import asyncio
import logging

from learn_pydantic_ai import run_worker
from workflows import StreamingWorkflow, event_counts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
)
_log = logging.getLogger(__name__)


async def main() -> None:
    _log.info("Watch this terminal for [event] ... lines as the workflow runs.")
    try:
        await run_worker(workflows=[StreamingWorkflow])
    finally:
        _log.info("event tally: %s", dict(event_counts))


if __name__ == "__main__":
    asyncio.run(main())
