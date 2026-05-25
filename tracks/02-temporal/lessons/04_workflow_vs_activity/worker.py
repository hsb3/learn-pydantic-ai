"""Lesson 04 — worker process.

Run me in terminal A:

    make temporal-04-worker

Same shape as Lesson 03. Because the agent's `@tool_plain` is reachable
via `__pydantic_ai_agents__`, `PydanticAIPlugin` will register the tool's
auto-generated activity for us — no manual `activities=[get_weather]`
needed.
"""

from __future__ import annotations

import asyncio
import logging

from learn_pydantic_ai import run_worker
from workflows import WeatherWorkflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


async def main() -> None:
    await run_worker(workflows=[WeatherWorkflow])


if __name__ == "__main__":
    asyncio.run(main())
