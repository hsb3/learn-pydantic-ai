"""Shared Temporal wiring for the durable-execution track.

Every lesson's `worker.py` and starter imports from here so the per-lesson
files stay focused on what's new (the workflow + the agent) instead of
re-typing the same `Client.connect(...)` glue.

Key Constants:
    TASK_QUEUE: The task queue every lesson worker listens on.
    NAMESPACE: The Temporal namespace the docker stack creates by default.
    TEMPORAL_ADDRESS: Default gRPC frontend address for the docker stack.

Key Functions:
    connect(): Return a Temporal `Client` wired with `PydanticAIPlugin`.

Dependencies:
    - temporalio: SDK client + worker.
    - pydantic_ai.durable_exec.temporal: PydanticAIPlugin (data converter
      + workflow sandbox passthroughs).

Example:
    >>> from learn_pydantic_ai.temporal import connect, TASK_QUEUE
    >>> client = await connect()
    >>> handle = await client.start_workflow(
    ...     MyWorkflow.run, "hello", id="wf-1", task_queue=TASK_QUEUE,
    ... )
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from typing import Final

from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from temporalio.client import Client
from temporalio.worker import Worker, WorkflowRunner
from temporalio.worker.workflow_sandbox import (
    SandboxedWorkflowRunner,
    SandboxRestrictions,
)

TASK_QUEUE: Final[str] = "learn-pydantic-ai"
NAMESPACE: Final[str] = "learn-pydantic-ai"
TEMPORAL_ADDRESS: Final[str] = "localhost:7233"

_log = logging.getLogger(__name__)


async def connect(
    *,
    address: str | None = None,
    namespace: str | None = None,
) -> Client:
    """Connect to your local Temporal server with the PydanticAI plugin.

    Reads `TEMPORAL_ADDRESS` and `TEMPORAL_NAMESPACE` from the environment
    if the corresponding kwargs are not passed — that's how `docker compose`
    overrides get applied without touching code.
    """
    return await Client.connect(
        address or os.getenv("TEMPORAL_ADDRESS", TEMPORAL_ADDRESS),
        namespace=namespace or os.getenv("TEMPORAL_NAMESPACE", NAMESPACE),
        plugins=[PydanticAIPlugin()],
    )


def make_workflow_runner() -> WorkflowRunner:
    """Return a `SandboxedWorkflowRunner` that passes through this package.

    `learn_pydantic_ai/__init__.py` calls `Path(__file__).resolve()` and
    `load_dotenv(...)` at import time. Both are restricted operations in
    the workflow sandbox. Marking the module as pass-through tells the
    sandbox to reuse the already-loaded instance instead of re-importing
    inside the sandbox.

    `PydanticAIPlugin` adds its own passthroughs (`pydantic_ai`,
    `pydantic`, `httpx`, …) on top of this when the worker is configured.
    """
    return SandboxedWorkflowRunner(
        restrictions=SandboxRestrictions.default.with_passthrough_modules(
            "learn_pydantic_ai",
        ),
    )


async def run_worker(
    workflows: list[type],
    activities: list = None,  # type: ignore[type-arg]
    *,
    task_queue: str = TASK_QUEUE,
    extra_plugins: list = None,  # type: ignore[type-arg]
) -> None:
    """Run a worker forever until SIGINT/SIGTERM.

    Used by every lesson's `worker.py`. Centralizing this keeps each
    lesson's worker down to a list of workflows + activities to register.

    `PydanticAIPlugin` is applied via the Client (`connect()`), and the
    Worker inherits client plugins — so we do NOT pass it explicitly here.
    Doing so would double-register the auto-generated activities from each
    workflow's `__pydantic_ai_agents__` attribute and crash worker startup.
    `extra_plugins` is for things that AREN'T client plugins, like
    `LogfirePlugin` in Lesson 08.
    """
    activities = activities or []
    extra_plugins = extra_plugins or []
    client = await connect()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    # Important: do NOT pass `PydanticAIPlugin` to the Worker — the Client
    # already has it via `connect()`, and Temporal propagates client plugins
    # to the Worker. Passing it twice double-registers activities and crashes
    # at worker startup. Extra plugins (e.g. `LogfirePlugin`) are still
    # passed here because they are NOT applied via the client.
    async with Worker(
        client,
        task_queue=task_queue,
        workflows=workflows,
        activities=activities,
        plugins=extra_plugins,
        workflow_runner=make_workflow_runner(),
    ):
        _log.info(
            "Worker started — task_queue=%s, workflows=%s. Ctrl-C to stop.",
            task_queue,
            [w.__name__ for w in workflows],
        )
        await stop.wait()


__all__ = [
    "NAMESPACE",
    "TASK_QUEUE",
    "TEMPORAL_ADDRESS",
    "connect",
    "make_workflow_runner",
    "run_worker",
]
