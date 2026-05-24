"""Lesson 02 — worker process.

Run me in terminal A:

    make temporal-02-worker

Same one-liner as every other lesson's worker. `run_worker` installs
`PydanticAIPlugin` via the client — harmless here since there's no agent
for it to wire up; it just sits dormant until Lesson 03. `TallyWorkflow`
registers no activities, so there's nothing to pass alongside it.
"""

from __future__ import annotations

import asyncio
import logging

from learn_pydantic_ai import run_worker
from workflows import TallyWorkflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


async def main() -> None:
    await run_worker(workflows=[TallyWorkflow])


if __name__ == "__main__":
    asyncio.run(main())
