"""ThreadWorkflow — one long-lived workflow per langgraph "thread".

This is the structural bet that makes the whole contract fall out cleanly:

  langgraph concept        ->  Temporal mechanism
  -----------------------------------------------
  thread                   ->  one workflow (workflow_id == thread_id)
  run (new turn)           ->  submit_run signal
  GET state / history      ->  query
  HITL interrupt           ->  workflow pauses on wait_condition
  resume an interrupt      ->  resume signal
  cancel a run             ->  cancel_run signal
  streaming                ->  activities publish to Redis (see streaming_publish)

The actor loop (wait_condition on a pending queue) is lifted directly from
Pydantic AI's official temporal example (SlackThreadWorkflow).
"""
from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from worker.activities import publish_activity, publish_terminal_activity
    from worker.agents import REGISTRY, Deps

_HISTORY_LIMIT = 8000  # continue-as-new before history grows unbounded


@workflow.defn
class ThreadWorkflow:
    def __init__(self) -> None:
        self._messages: list[dict[str, Any]] = []
        self._pending: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._runs: dict[str, str] = {}                 # run_id -> status
        self._interrupt: dict[str, Any] | None = None   # {"run_id", "value"}
        self._resume: dict[str, Any] = {}               # run_id -> resume value
        self._cancelled: set[str] = set()
        self._metadata: dict[str, Any] = {}

    # ---- run loop -------------------------------------------------------
    @workflow.run
    async def run(self, init: dict[str, Any] | None = None) -> None:
        if init:
            self._metadata = init.get("metadata", {})
            self._messages = init.get("messages", [])    # carried across continue-as-new
        while True:
            await workflow.wait_condition(lambda: not self._pending.empty())
            while not self._pending.empty():
                await self._process(self._pending.get_nowait())
            if workflow.info().get_current_history_length() > _HISTORY_LIMIT:
                # TODO(prod): externalize messages to Supabase and carry a ref,
                # not the full list (2MB payload ceiling on event history).
                workflow.continue_as_new(
                    args=[{"metadata": self._metadata, "messages": self._messages}]
                )

    async def _process(self, req: dict[str, Any]) -> None:
        run_id: str = req["run_id"]
        if run_id in self._cancelled:
            self._runs[run_id] = "cancelled"
            return
        self._runs[run_id] = "running"
        await self._publish(run_id, "values", {"status": "running"})

        if req.get("input"):
            self._messages.append(req["input"])
        agent = REGISTRY[req["agent"]]

        try:
            result = await agent.run(_render(self._messages), deps=Deps(run_id=run_id))
            output = str(result.output)

            # --- HITL demonstration: agent signals it needs the human ---
            if output.startswith("__INTERRUPT__"):
                self._interrupt = {"run_id": run_id, "value": output.removeprefix("__INTERRUPT__")}
                self._runs[run_id] = "interrupted"
                await self._publish(run_id, "interrupt", self._interrupt["value"])
                await workflow.wait_condition(
                    lambda: run_id in self._resume or run_id in self._cancelled
                )
                if run_id in self._cancelled:
                    self._runs[run_id] = "cancelled"
                    return
                self._messages.append({"role": "user", "content": f"(resumed) {self._resume.pop(run_id)}"})
                self._interrupt = None
                result = await agent.run(_render(self._messages), deps=Deps(run_id=run_id))
                output = str(result.output)

            self._messages.append({"role": "assistant", "content": output})
            self._runs[run_id] = "success"
            await self._publish_terminal(run_id, "values", {"output": output})
        except Exception as exc:  # noqa: BLE001 - surface as a run error event
            self._runs[run_id] = "error"
            await self._publish_terminal(run_id, "error", {"message": str(exc)})

    # ---- signals (the "write" side of the contract) --------------------
    @workflow.signal
    async def submit_run(self, req: dict[str, Any]) -> None:
        await self._pending.put(req)

    @workflow.signal
    def resume(self, run_id: str, value: Any) -> None:
        self._resume[run_id] = value

    @workflow.signal
    def cancel_run(self, run_id: str) -> None:
        self._cancelled.add(run_id)

    # ---- queries (the "read" side of the contract) ---------------------
    @workflow.query
    def get_state(self) -> dict[str, Any]:
        return {
            "values": {"messages": self._messages},
            "interrupts": [self._interrupt] if self._interrupt else [],
            "status": self._status(),
        }

    @workflow.query
    def get_history(self) -> list[dict[str, Any]]:
        return self._messages

    @workflow.query
    def get_run_status(self, run_id: str) -> str | None:
        return self._runs.get(run_id)

    @workflow.query
    def status(self) -> str:
        return self._status()

    # ---- helpers --------------------------------------------------------
    def _status(self) -> str:
        if self._interrupt:
            return "interrupted"
        return "busy" if any(s == "running" for s in self._runs.values()) else "idle"

    async def _publish(self, run_id: str, event: str, data: Any) -> None:
        await workflow.execute_activity(
            publish_activity, args=[run_id, event, data],
            start_to_close_timeout=timedelta(seconds=10),
        )

    async def _publish_terminal(self, run_id: str, event: str, data: Any) -> None:
        await workflow.execute_activity(
            publish_terminal_activity, args=[run_id, event, data],
            start_to_close_timeout=timedelta(seconds=10),
        )


def _render(messages: list[dict[str, Any]]) -> str:
    # Scaffold: stringify the thread (as the Pydantic AI example does).
    # Refinement: thread proper pydantic-ai ModelMessage history instead.
    return "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)
