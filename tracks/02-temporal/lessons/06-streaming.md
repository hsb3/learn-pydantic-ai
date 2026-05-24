# Lesson 06 — Streaming events via `event_stream_handler`

**Code:** `../examples/06_streaming/`

## Review

- In Lesson 05 you tuned `ActivityConfig` — setting per-tool timeouts and retry policies on the activities pydantic-ai auto-generates.
- All that tuning lived in the config; the workflow body stayed a clean `await agent.run(...)`.

## Goal

Pipe per-token model events and tool-call events out of a workflow while
keeping the workflow body itself as the simple `await agent.run(...)` call
you already know. The trick: register a handler on the `TemporalAgent`
and let pydantic-ai lift it into a Temporal activity for you.

## TL;DR

Here you pipe per-token model events and tool-call events out of a workflow by registering an `event_stream_handler` on the `TemporalAgent`, while the workflow body stays the simple `await agent.run(...)` you already know. The key mechanic: `agent.run_stream()` is forbidden inside the deterministic workflow sandbox, so pydantic-ai lifts your handler into an activity (invoked once per event) to give you streaming visibility durably. The canonical shape is in [Pattern](#pattern).

## Why it matters

Token-by-token streaming is the UX expectation for chat-style agents.
Outside Temporal, `agent.run_stream()` is how you get it. Inside a
Temporal workflow the determinism sandbox forbids that API — you cannot
hold an async-iterator across `await` points whose outcome the sandbox
must reproduce on replay. The workaround is `event_stream_handler`: you
hand pydantic-ai a coroutine, it forwards every event to it from inside
an activity, and your workflow stays clean.

In LangGraph terms: think of `event_stream_handler` as the equivalent of
the `astream_events()` callback you'd hook on a graph, except the callback
runs in a worker-managed activity instead of the graph's own coroutine.

## Mental model

```
                           [ workflow body ]
                                 │
                       await agent.run(prompt)
                                 │
       ┌─────────────────────────┼─────────────────────────┐
       ▼                         ▼                         ▼
  model activity            tool activity         event_stream_handler activity
   per request               per call           per AgentStreamEvent received
```

Every event is shipped as a separate activity invocation. Your handler
gets `(ctx, stream)` where `stream` is the **one** event for this activity
call (wrapped as a single-item async iterable so the handler's body
`async for event in stream:` reads naturally). The handler can do I/O —
it's a normal activity.

## Walk the code

- `workflows.py:42` — `log_events(ctx, stream)` is the handler. It
  consumes the (single-event) stream and updates a module-level
  `Counter`. Anything you'd want to print, log, or forward goes here.
- `workflows.py:73` — `TemporalAgent(_base, event_stream_handler=log_events)`.
  **The handler is set on the `TemporalAgent`, not on the underlying
  `Agent`.** If you set it on `_base` instead, pydantic-ai's wrapper logic
  won't lift it into an activity correctly inside a workflow.
- `workflows.py:88` — workflow body is still just `await agent.run(...)`.
  No `run_stream` API, no async-iterator state held in the workflow.

## Run

```bash
# Terminal A — server (skip if already up)
make temporal-up

# Terminal A — worker. Watch this terminal for [event] ... lines.
make temporal-06-worker

# Terminal B — starter
make temporal-06
```

The worker's stdout will show one line per non-delta `AgentStreamEvent`:
`part_start`, `function_tool_call`, `function_tool_result`, `part_end`,
`final_result`. (`part_delta` events — the per-token chunks — are
filtered out in the demo handler to keep the output readable; remove the
filter to see the full firehose.)

## Try it

1. **See the deltas.** Delete the `if kind == "part_delta": continue`
   block in `log_events`. Restart the worker. Run again. You'll see one
   `part_delta` event per token chunk — that's the streaming firehose.
2. **Push events to a queue.** Replace `print(...)` with `redis.publish(...)`
   or a `asyncio.Queue.put_nowait(...)` to fan events out to a websocket
   or SSE consumer. Because the handler runs in an activity, real I/O
   like a Redis connection is fine.
3. **Try the forbidden API.** Add `async with streaming_agent.run_stream(...)`
   inside the workflow body. Restart the worker, run, and read the
   `UserError`: "`agent.run_stream()` cannot be used inside a Temporal
   workflow. Set an `event_stream_handler` ..."

## Gotchas

- **Handler goes on `TemporalAgent`, not `Agent`.** The wrapper is what
  lifts it into an activity. A handler on the inner agent is ignored
  inside a workflow.
- **The "stream" inside the handler is a one-event async iterable.**
  Don't expect to receive all events through a single call — you'll be
  invoked once per event. Keep tallies in module-level state if you
  want a final summary at the end.
- **No long blocking work in the handler.** Each event becomes its own
  activity invocation. A slow handler (network call per event) tanks
  throughput. Move heavy lifting to a downstream consumer reading from
  your queue.
- **`agent.run_stream()` and `agent.run_stream_events()` are forbidden
  inside workflows.** Only `agent.run()` is allowed. The error message
  if you forget points you at this lesson's pattern.

## Bridge

You've now seen pydantic-ai's runtime knobs: retries, timeouts, and
streaming. Lesson 07 adds **human-in-the-loop**: pause a workflow on a
signal, wait for approval, then resume.

## Pattern

*The canonical shape, for the re-read.*

```python
from collections.abc import AsyncIterable
from pydantic_ai import RunContext
from pydantic_ai.messages import AgentStreamEvent
from temporalio import activity

async def log_events(ctx: RunContext, stream: AsyncIterable[AgentStreamEvent]) -> None:
    async for event in stream:                # MUST consume the stream
        activity.logger.info("stream event %s", event.event_kind)

my_agent = TemporalAgent(_base, event_stream_handler=log_events)
```

The handler runs as a Temporal activity, so it can do regular I/O. `agent.run_stream()` is FORBIDDEN inside a workflow — `event_stream_handler` is how you get per-token visibility durably.
