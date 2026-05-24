"""Lesson 11 capstone — worker process with Logfire observability.

Runs locally via `make temporal-11-worker` (against `make temporal-up`)
or inside Docker via `make temporal-11-up` (compose stack at
`./docker-compose.yml`).

Wires three things at startup:
    - `LogfirePlugin` — Lesson 09, sends every activity to Logfire when
      `LOGFIRE_TOKEN` is set (silent no-op otherwise).
    - `CapstoneWorkflow` — the workflow class itself.
    - `fetch_external_context` — Lesson 08 custom long-running activity.
"""

from __future__ import annotations

import asyncio
import logging
import os

import logfire
from pydantic_ai.durable_exec.temporal import LogfirePlugin

from activities import fetch_external_context
from learn_pydantic_ai import run_worker
from workflow import CapstoneWorkflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
_log = logging.getLogger("capstone.worker")


def _configure_logfire() -> None:
    """Configure Logfire — no-op if `LOGFIRE_TOKEN` is unset."""
    logfire.configure(
        service_name="learn-pydantic-ai-capstone",
        send_to_logfire="if-token-present",
        scrubbing=False,
    )
    logfire.instrument_pydantic_ai()
    logfire.instrument_httpx(capture_all=True)
    if os.getenv("LOGFIRE_TOKEN"):
        _log.info("Logfire enabled — traces at https://logfire.pydantic.dev")
    else:
        _log.info("LOGFIRE_TOKEN not set — Logfire instrumented but not transmitting")


async def main() -> None:
    _configure_logfire()
    await run_worker(
        workflows=[CapstoneWorkflow],
        activities=[fetch_external_context],
        extra_plugins=[LogfirePlugin()],
    )


if __name__ == "__main__":
    asyncio.run(main())
