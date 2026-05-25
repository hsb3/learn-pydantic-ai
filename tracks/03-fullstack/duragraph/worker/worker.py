"""Worker entrypoint:  python -m worker.worker

Hosts the ThreadWorkflow + activities, and registers each agent via
AgentPlugin so its model/tool calls run as activities. Scale these replicas
on task-queue backlog (KEDA), min replicas >= 1 — see the Azure topology.
"""
from __future__ import annotations

import asyncio

from pydantic_ai.durable_exec.temporal import AgentPlugin
from temporalio.worker import Worker

from app.core.config import get_settings
from worker.activities import ALL_ACTIVITIES
from worker.agents import REGISTRY
from worker.client import build_client
from worker.workflows import ThreadWorkflow


async def main() -> None:
    s = get_settings()
    client = await build_client()
    async with Worker(
        client,
        task_queue=s.task_queue,
        workflows=[ThreadWorkflow],
        activities=ALL_ACTIVITIES,
        plugins=[AgentPlugin(a) for a in REGISTRY.values()],
    ):
        print(f"worker up on task_queue={s.task_queue}")
        await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
