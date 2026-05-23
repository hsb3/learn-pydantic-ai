"""07 — Streaming output.

Up to now we've called `run_sync()` and waited for the full result. For
chat UIs and long-running responses you want tokens as soon as the model
produces them.

`run_stream()` is an *async context manager* that yields a
`StreamedRunResult`. Call `.stream_text(delta=True)` on it to get an async
iterator of token deltas (incremental chunks), or `.stream_text()` to get
the full accumulated text at each step.

Note: streaming makes the run async. Use `asyncio.run(main())` for sync
entry points like this CLI script.
"""

from __future__ import annotations

import asyncio
import sys

from pydantic_ai import Agent

from learn_pydantic_ai import FLASH


agent = Agent(
    FLASH,
    instructions="Be vivid. Write 3-4 sentences.",
)


async def main() -> None:
    async with agent.run_stream("Describe a stormy seascape at dusk.") as stream:
        async for delta in stream.stream_text(delta=True):
            sys.stdout.write(delta)
            sys.stdout.flush()
        print()  # newline at end
        print("---")
        # The accumulated usage is available once the stream finishes.
        print(stream.usage)


if __name__ == "__main__":
    asyncio.run(main())
