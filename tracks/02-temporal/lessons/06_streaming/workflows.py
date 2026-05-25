"""Lesson 06 — stream model + tool events out of a workflow.

The workflow body itself stays clean: `await agent.run(...)` and return the
output. But every per-token model chunk and every tool-call event flows
through `event_stream_handler` — a callback registered on `TemporalAgent`
that the plugin lifts into its own Temporal activity.

You CANNOT use `agent.run_stream()` or `agent.run_stream_events()` inside a
workflow — the determinism sandbox blocks the async streaming primitives.
Instead, set `event_stream_handler=` on the wrapper and call the normal
`agent.run()`. Pydantic AI funnels every `AgentStreamEvent` to your handler
as it happens.

The handler executes inside an activity. That means it can do regular
Python I/O (print, write to disk, send to a queue) without violating
determinism — but it can't block for long because it counts against the
activity's `start_to_close_timeout` per event.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import AsyncIterable

from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import AgentStreamEvent
from pydantic_ai.durable_exec.temporal import PydanticAIWorkflow, TemporalAgent
from temporalio import activity, workflow

from learn_pydantic_ai import FLASH


# Module-level tally. The handler runs in the activity worker process, so
# this Counter is the one in the worker — not the workflow. Restarting the
# worker resets it. Good enough for a teaching demo.
event_counts: Counter[str] = Counter()


async def log_events(
    ctx: RunContext[None],
    stream: AsyncIterable[AgentStreamEvent],
) -> None:
    """Receive every stream event, log it, and bump a counter.

    Pydantic AI calls this once per agent run and feeds events as they
    arrive. The function MUST consume the stream (`async for event in stream`)
    — that's the protocol. You may otherwise do anything: log, push to a
    queue, write SSE frames to a client connection, etc.
    """
    async for event in stream:
        kind = event.event_kind
        event_counts[kind] += 1
        # Avoid spamming the log with text-delta events; just summarise.
        if kind == "part_delta":
            continue
        # The handler runs as a Temporal activity, so `activity.logger`
        # routes through the worker's logging chain (including Logfire if
        # attached). `print()` would just hit stdout and be lost.
        activity.logger.info("stream event %s: %r", kind, event)


async def double(x: int) -> int:
    """Double a number. A tool here just to make the event stream more interesting."""
    return x * 2


_base = Agent(
    model=FLASH,
    name="streaming_agent",
    instructions=(
        "When the user gives you a number, call `double` on it once, then "
        "report the doubled value back in one short sentence."
    ),
)
_base.tool_plain(double)


streaming_agent = TemporalAgent(
    _base,
    # The handler MUST be set here (on the TemporalAgent), not on the
    # underlying Agent. The plugin lifts this into its own activity so the
    # workflow body itself stays deterministic.
    event_stream_handler=log_events,
)


@workflow.defn
class StreamingWorkflow(PydanticAIWorkflow):
    """Run the agent normally — streaming happens through the handler."""

    __pydantic_ai_agents__ = [streaming_agent]

    @workflow.run
    async def run(self, prompt: str) -> str:
        # No `run_stream`! The sandbox would reject it. Plain `run()` plus
        # the registered handler gives us streaming-shaped behavior in a
        # durable setting.
        result = await streaming_agent.run(prompt)
        return result.output
