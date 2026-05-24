"""Lesson 09 — worker process with `LogfirePlugin`.

Run me in terminal A:

    make temporal-09-worker

Two things make this worker different from Lesson 03's:

1. We call `logfire.configure(...)` in `main()` BEFORE starting the worker.
   This sets up the OpenTelemetry tracer that `LogfirePlugin` will hand to
   Temporal's tracing interceptor.
2. We pass `extra_plugins=[LogfirePlugin()]` to `run_worker`. That plugin
   wires Temporal's `TracingInterceptor` so every workflow + activity gets
   an OTel span — and, because we also called
   `logfire.instrument_pydantic_ai()`, the spans the agent emits nest under
   the activity spans automatically.

`send_to_logfire="if-token-present"` means: if `LOGFIRE_TOKEN` is set, ship
the traces to https://logfire.pydantic.dev; if not, the SDK is still active
(spans still get created and nested) but the network exporter is a no-op.
That's why this lesson works fine without a Logfire account.
"""

from __future__ import annotations

import asyncio
import logging
import os

import logfire
from pydantic_ai.durable_exec.temporal import LogfirePlugin

from learn_pydantic_ai import run_worker
from workflows import ResearchWorkflow

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")


def _configure_logfire() -> None:
    """Configure Logfire for this worker process.

    Called once at startup BEFORE `run_worker(...)`. It is invalid to call
    `logfire.configure()` from inside `@workflow.run` — the workflow sandbox
    treats it as non-deterministic I/O.
    """
    logfire.configure(
        service_name="learn-pydantic-ai-lesson-09",
        # Graceful degradation: ship traces only if LOGFIRE_TOKEN is set.
        send_to_logfire="if-token-present",
        scrubbing=False,
    )
    # Emit Pydantic AI's first-class spans for `Agent.run`, tool calls,
    # model requests, structured-output parsing, etc.
    logfire.instrument_pydantic_ai()
    # Bonus: see the actual HTTP POST to the model provider as a nested span
    # under each model-request activity.
    logfire.instrument_httpx(capture_all=True)

    if os.getenv("LOGFIRE_TOKEN"):
        print("Logfire enabled — traces at https://logfire.pydantic.dev")
    else:
        print(
            "LOGFIRE_TOKEN not set — running in no-op mode "
            "(Logfire instrumentation active but not transmitting)."
        )


async def main() -> None:
    _configure_logfire()
    await run_worker(
        workflows=[ResearchWorkflow],
        extra_plugins=[LogfirePlugin()],
    )


if __name__ == "__main__":
    asyncio.run(main())
