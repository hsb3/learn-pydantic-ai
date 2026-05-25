"""Pydantic AI agents, wrapped for durable execution on Temporal.

`TemporalAgent` turns an ordinary Pydantic AI agent into a Temporal workflow
component — every model request, tool call, and MCP call automatically becomes
a retryable activity. You write normal agent code; durability is the wrapper.

The REGISTRY is your "assistants" backing: assistant_id -> agent key.

Verified against pydantic-ai 1.102.0 / temporalio 1.27.2.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent, RunContext
from pydantic_ai.durable_exec.temporal import TemporalAgent

from worker.streaming_publish import publish_event


@dataclass
class Deps:
    """Threaded into every agent run so tools + the stream handler know which
    run to publish deltas for. `agent.run(prompt, deps=Deps(run_id=...))`."""
    run_id: str


# --- a basic chat agent; replace/extend with your scoping/SQL/code agents ---
chat_agent = Agent(
    # pydantic-ai 1.x: "openai:" = Chat Completions. In v2.0 it will default to
    # the Responses API — pin "openai-chat:gpt-4o" if you want to lock current behavior.
    "openai:gpt-4o",
    deps_type=Deps,
    system_prompt="You are a helpful analyst assistant for risk-bearing healthcare orgs.",
)


@chat_agent.tool
async def echo_context(ctx: RunContext[Deps], note: str) -> str:
    """Example tool. Real tools (SQL, code exec) become Temporal activities
    automatically under TemporalAgent."""
    return f"[run {ctx.deps.run_id}] {note}"


async def event_stream_handler(ctx: RunContext[Deps], stream: Any) -> None:
    """STREAMING SEAM (the langgraph-api 'magic' you were missing).

    Runs inside the model activity; forwards Pydantic AI stream events to the
    Redis channel for this run, tagged with langgraph stream_mode names so the
    browser's existing switch statement is unchanged:

        messages -> assistant answer tokens
        updates  -> tool call started / tool result
        events   -> thinking deltas, tool-arg deltas, final-result marker

    We switch on stable discriminator fields (event_kind / part_delta_kind)
    rather than isinstance, so this survives pydantic-ai refactors.

    Retry caveat (Temporal Workflow Streams docs): a retried model activity is
    a fresh publisher and replays deltas. The client should reset accumulated
    text on a new attempt; every text delta carries `index` to enable that.
    """
    run_id = ctx.deps.run_id
    async for event in stream:
        ek = event.event_kind

        if ek == "part_delta":
            delta = event.delta
            dk = delta.part_delta_kind
            if dk == "text" and delta.content_delta:
                await publish_event(run_id, "messages",
                                    {"type": "text", "index": event.index, "delta": delta.content_delta})
            elif dk == "thinking" and delta.content_delta:
                await publish_event(run_id, "events",
                                    {"type": "thinking", "index": event.index, "delta": delta.content_delta})
            elif dk == "tool_call":
                await publish_event(run_id, "events",
                                    {"type": "tool_args", "index": event.index,
                                     "tool_call_id": delta.tool_call_id, "delta": _jsonable(delta.args_delta)})

        elif ek == "part_start":
            part = event.part
            if part.part_kind == "text" and part.content:
                await publish_event(run_id, "messages",
                                    {"type": "text", "index": event.index, "delta": part.content})
            elif part.part_kind == "thinking" and part.content:
                await publish_event(run_id, "events",
                                    {"type": "thinking", "index": event.index, "delta": part.content})

        elif ek == "function_tool_call":
            p = event.part
            await publish_event(run_id, "updates",
                                {"type": "tool_call", "tool": p.tool_name,
                                 "tool_call_id": p.tool_call_id, "args": _jsonable(p.args)})

        elif ek == "function_tool_result":
            await publish_event(run_id, "updates",
                                {"type": "tool_result",
                                 "tool_call_id": getattr(event.part, "tool_call_id", None),
                                 "content": _jsonable(event.content)})

        elif ek == "final_result":
            await publish_event(run_id, "events",
                                {"type": "final_result", "tool": event.tool_name})
        # part_end / builtin_tool_* intentionally ignored; forward as "events" if needed.


def _jsonable(v: Any) -> Any:
    """Tool args/results may be raw JSON strings, dicts, or domain objects.
    Keep primitives/containers as-is; stringify anything else. publish_event
    also json-dumps with default=str as a final backstop."""
    if isinstance(v, (str, int, float, bool, type(None), list, dict)):
        return v
    return str(v)


# Wrap once. AgentPlugin(temporal_chat) is registered on the Worker.
temporal_chat = TemporalAgent(
    chat_agent,
    name="chat",
    event_stream_handler=event_stream_handler,
)

# assistant agent-key -> TemporalAgent
REGISTRY: dict[str, TemporalAgent] = {
    "chat": temporal_chat,
}
