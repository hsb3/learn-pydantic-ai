"""The brain. Maps the langgraph-shaped operations onto Temporal client calls.

Deliberately addresses the workflow by STRING name ("ThreadWorkflow",
"submit_run", ...) so the API process never imports the agent/model stack —
only the worker does. Keeps the API image small and the layers clean.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from temporalio.client import Client, WorkflowExecutionStatus
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.service import RPCError

from app.core.config import get_settings
from app.core.errors import AssistantNotFound, RunNotFound, ThreadNotFound, WorkerUnavailable
from app.schemas import Assistant, Run, RunCreate, RunStatus, Thread, ThreadState

_QUERY_TIMEOUT = 5.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TemporalGateway:
    def __init__(self, client: Client) -> None:
        self._client = client
        self._tq = get_settings().task_queue
        # Scaffold assistant store. Swap for Supabase: assistants table.
        self._assistants: dict[str, Assistant] = {
            "asst_chat": Assistant(
                assistant_id="asst_chat", name="Chat", agent="chat", config={}, created_at=_now()
            )
        }

    # ---- assistants ----
    def create_assistant(self, name: str, agent: str, config: dict) -> Assistant:
        a = Assistant(assistant_id=f"asst_{uuid4().hex[:8]}", name=name, agent=agent,
                      config=config, created_at=_now())
        self._assistants[a.assistant_id] = a
        return a

    def get_assistant(self, assistant_id: str) -> Assistant:
        if assistant_id not in self._assistants:
            raise AssistantNotFound(f"unknown assistant {assistant_id}")
        return self._assistants[assistant_id]

    # ---- threads ----
    async def create_thread(self, metadata: dict) -> Thread:
        thread_id = f"thread_{uuid4().hex}"
        await self._client.start_workflow(
            "ThreadWorkflow",
            args=[{"metadata": metadata}],
            id=thread_id,
            task_queue=self._tq,
            id_conflict_policy=WorkflowIDConflictPolicy.FAIL,
        )
        return Thread(thread_id=thread_id, status="idle", metadata=metadata, created_at=_now())

    async def get_state(self, thread_id: str) -> ThreadState:
        state = await self._query(thread_id, "get_state")
        return ThreadState(
            thread_id=thread_id,
            values=state.get("values", {}),
            interrupts=state.get("interrupts", []),
            next=[],
        )

    async def get_history(self, thread_id: str) -> list[dict]:
        return await self._query(thread_id, "get_history")

    # ---- runs ----
    async def create_run(self, thread_id: str, body: RunCreate, run_id: str | None = None) -> Run:
        handle = await self._require_thread(thread_id)
        run_id = run_id or f"run_{uuid4().hex}"

        if body.command and body.command.resume is not None:
            # Resume an interrupted run rather than starting new work.
            await handle.signal("resume", args=[_interrupted_run_id(await self._query(thread_id, "get_state")), body.command.resume])
            return Run(run_id=run_id, thread_id=thread_id, assistant_id=body.assistant_id,
                       status=RunStatus.running, created_at=_now())

        assistant = self.get_assistant(body.assistant_id)
        await handle.signal("submit_run", {
            "run_id": run_id,
            "agent": assistant.agent,
            "input": (body.input or {}).get("messages", [{}])[-1] if body.input else None,
            "config": {**assistant.config, **body.config},
        })
        return Run(run_id=run_id, thread_id=thread_id, assistant_id=body.assistant_id,
                   status=RunStatus.pending, created_at=_now())

    async def get_run(self, thread_id: str, run_id: str) -> Run:
        status = await self._query(thread_id, "get_run_status", run_id)
        if status is None:
            raise RunNotFound(f"run {run_id} not found on thread {thread_id}")
        return Run(run_id=run_id, thread_id=thread_id, assistant_id="",
                   status=RunStatus(status), created_at=_now())

    async def cancel_run(self, thread_id: str, run_id: str) -> None:
        handle = await self._require_thread(thread_id)
        await handle.signal("cancel_run", run_id)

    # ---- helpers ----
    async def _require_thread(self, thread_id: str):
        handle = self._client.get_workflow_handle(thread_id)
        try:
            desc = await handle.describe()
        except RPCError as exc:
            raise ThreadNotFound(f"thread {thread_id} not found") from exc
        if desc.status not in (WorkflowExecutionStatus.RUNNING, None):
            raise ThreadNotFound(f"thread {thread_id} is not active ({desc.status})")
        return handle

    async def _query(self, thread_id: str, name: str, *args):
        handle = self._client.get_workflow_handle(thread_id)
        try:
            return await asyncio.wait_for(handle.query(name, *args), timeout=_QUERY_TIMEOUT)
        except RPCError as exc:
            raise ThreadNotFound(f"thread {thread_id} not found") from exc
        except asyncio.TimeoutError as exc:
            raise WorkerUnavailable("query timed out — worker may be down") from exc


def _interrupted_run_id(state: dict) -> str:
    interrupts = state.get("interrupts") or []
    if not interrupts:
        raise RunNotFound("no interrupted run to resume")
    return interrupts[0]["run_id"]
