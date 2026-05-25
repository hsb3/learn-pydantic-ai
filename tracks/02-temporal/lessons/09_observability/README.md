# Lesson 09 — Observability with Logfire

> The code for this lesson is the three `.py` files in this folder. Read this
> page top to bottom; it quotes every part of the code you need to see.

## Review

In Lesson 08 you kept a long-running activity alive across the cluster's
liveness checks with `activity.heartbeat()` and tuned `start_to_close_timeout`
/ `heartbeat_timeout` so retries only fired on genuine death.

## Goal

Wire `LogfirePlugin` into a Temporal worker so every workflow execution becomes
a Logfire trace — with model requests, tool calls, and even the underlying HTTP
calls as nested spans.

## Files in this lesson

| File | Role |
|---|---|
| `workflows.py` | Defines `ResearchWorkflow`, a standard `PydanticAIWorkflow` with two tools. Deterministic — nothing here knows about Logfire. |
| `worker.py` | The **worker process**. **This is where the Logfire wiring lives** — `logfire.configure()` and `extra_plugins=[LogfirePlugin()]` — outside the workflow code, because configuration is non-deterministic I/O. Run in **terminal A**. |
| `example.py` | The **client**. Starts the workflow with one multi-step question and awaits the result. Run in **terminal B**. |

Why this three-file layout, and how much of it Temporal actually requires:
[Anatomy of a Temporal lesson](../../README.md#anatomy-of-a-temporal-lesson).

## How it works

The Temporal UI shows you *workflow history* — every activity scheduled,
started, completed, retried. It does **not** show you what the agent was
actually *thinking*: token usage, structured-output parsing, the exact JSON
sent to the model. Logfire fills that gap. Wire both, and you get end-to-end
correlation: click a workflow in Temporal → jump to its Logfire trace → drill
into the LLM call that took 6 seconds.

You get there by adding `LogfirePlugin` to the worker's `extra_plugins=` and
calling `logfire.configure()` once at startup, instrumenting pydantic-ai and
httpx. One `ResearchWorkflow` execution then becomes a trace tree like this:

```
Workflow span  [ResearchWorkflow]
├── Activity span  [researcher__model_request]
│   └── HTTP span  POST generativelanguage.googleapis.com/...
├── Activity span  [researcher__look_up_population]
├── Activity span  [researcher__look_up_currency]
└── Activity span  [researcher__model_request]
    └── HTTP span  POST generativelanguage.googleapis.com/...
```

Three pieces of instrumentation build that tree:

- **`LogfirePlugin`** registers Temporal's OpenTelemetry tracing interceptor,
  so the *workflow* and *activity* spans come for free.
- **`logfire.instrument_pydantic_ai()`** adds the *Agent.run* + tool-call spans
  inside each activity.
- **`logfire.instrument_httpx(capture_all=True)`** adds the *HTTP* spans inside
  each model-request span.

The single key mechanic is that the Logfire wiring lives **outside** the
workflow body. Why is the setup in `worker.py` and not `workflows.py`? Workflow
bodies must be deterministic — re-runnable from history without side effects.
`logfire.configure()` opens an OTel exporter, reads env vars, and writes to
disk: all forbidden inside a workflow sandbox. So you configure once at worker
boot, and the plugin handles the per-execution tracing. The canonical shape is
in [Pattern](#pattern).

## Coming from LangGraph?

The source for this section is titled "Coming from langgraph-api?" — kept here
under the standard heading.

Traces in LangSmith for a langgraph-api app map roughly 1:1 to traces in
Logfire here — same idea, same span tree, same drill-down ergonomics. The
difference is that Temporal also gives you the *workflow-history* view at
`localhost:8080`, which is finer-grained than LangSmith: every signal, every
retry, every timer is an event in history, not just a span. You end up with two
complementary views — Temporal for "what did the durable runtime do?", Logfire
for "what was the LLM thinking?".

## Walk the code

### `workflows.py` — the workflow class

A standard `PydanticAIWorkflow` with two tools. Nothing here knows about
Logfire; the workflow stays portable and deterministic.

**`look_up_population` and `look_up_currency`** are the two `@_base.tool_plain`
functions. They read hard-coded fact tables, so every run produces the same
trace tree — useful when you're learning to read Logfire spans.

```python
@_base.tool_plain
def look_up_population(city: str) -> str:
    """Return a string describing the population of `city`."""
    return _FACTS_POPULATION.get(city, f"No data for {city}")
```

**`researcher`** wraps the base agent in `TemporalAgent` *after* the tools are
registered, so `TemporalAgent` can lift each tool into its own activity.

```python
researcher = TemporalAgent(_base)
```

**`ResearchWorkflow.run`** is intentionally trivial — one `await
researcher.run(...)`. The interesting thing is what `LogfirePlugin` records
about that single call. Note `workflow.logger.info(...)`: the deterministic-safe
logger. Never call `print()` or `logfire.info()` directly inside a
`@workflow.run` body — the sandbox will reject it.

```python
@workflow.run
async def run(self, question: str) -> str:
    workflow.logger.info("ResearchWorkflow running for question=%r", question)
    result = await researcher.run(question)
    return result.output
```

### `worker.py` — the worker process

**`_configure_logfire`** is called once at startup, *before* `run_worker(...)`.
`logfire.configure(send_to_logfire="if-token-present", ...)` is a graceful
no-op when no token is present — the SDK stays active and spans still nest, but
the network exporter does nothing. That's the trick that keeps this lesson
cheap.

```python
logfire.configure(
    service_name="learn-pydantic-ai-lesson-09",
    send_to_logfire="if-token-present",
    scrubbing=False,
)
```

The same function adds the two extra layers of detail —
`logfire.instrument_pydantic_ai()` for the agent's first-class spans, and
`logfire.instrument_httpx(capture_all=True)` for the raw HTTP POST to the model
provider:

```python
logfire.instrument_pydantic_ai()
logfire.instrument_httpx(capture_all=True)
```

**`main`** runs the configuration, then starts the worker with
`extra_plugins=[LogfirePlugin()]`. `run_worker` already prepends
`PydanticAIPlugin()`, so the plugin order is `[PydanticAIPlugin(),
LogfirePlugin()]`. Order matters: `PydanticAIPlugin` must come first to register
activities; `LogfirePlugin` then wraps everything with tracing.

```python
async def main() -> None:
    _configure_logfire()
    await run_worker(
        workflows=[ResearchWorkflow],
        extra_plugins=[LogfirePlugin()],
    )
```

### `example.py` — the client

**`main`** sends one multi-step question. The agent calls *both* tools to answer
it, so the resulting Temporal history has multiple model-request and tool
activities — and if `LOGFIRE_TOKEN` is set, the Logfire trace shows the same
tree with HTTP-level detail. `execute_workflow` (not `start_workflow`) starts
the workflow and awaits its result in one call.

```python
result = await client.execute_workflow(
    ResearchWorkflow.run,
    "How big is Tokyo's population, and what currency does its country use?",
    id=workflow_id,
    task_queue=TASK_QUEUE,
)
```

## Run it

Server up first (`make temporal-up`, leave running), then two terminals — the
same pattern as every other lesson:

```bash
# Terminal A — worker (Ctrl-C to stop)
make temporal-09-worker
```

```bash
# Terminal B — starter
make temporal-09
```

Without `LOGFIRE_TOKEN` you'll see the worker print `LOGFIRE_TOKEN not set —
running in no-op mode`. The workflow still runs to completion; you just don't
get the shipped traces. Open `http://localhost:8080` and click your workflow to
see the standard Temporal history.

With `LOGFIRE_TOKEN=...` in `.env`, you'll see the worker print a
`https://logfire.pydantic.dev` URL. Click into the trace there — the same
workflow now has spans for every model call and every HTTP request.

## Try it

1. Sign up for a free Logfire account → create a write token → put
   `LOGFIRE_TOKEN=...` in `.env` → restart the worker → re-run. Open the
   printed URL.
2. Change `look_up_population` to `raise RuntimeError("simulated outage")`.
   Re-run. Compare what the *Temporal UI* shows (the activity went into retry)
   vs what *Logfire* shows (the exception span with stack trace).
3. Crank up the question complexity: `"For each of Tokyo, Paris, and São Paulo,
   give me the population and currency."` Watch the trace tree get deeper —
   more model requests, more tool calls.

## Gotchas

- **Never call `logfire.configure()` inside `@workflow.run`.** Configure once in
  the worker process before `run_worker(...)`. Logfire spans emitted from inside
  an activity are fine — the activity is normal Python, not sandboxed workflow
  code.
- **`LogfirePlugin` must come AFTER `PydanticAIPlugin` in the plugin list.**
  `run_worker` already prepends `PydanticAIPlugin`, so passing it via
  `extra_plugins=` is correct.
- **`send_to_logfire="if-token-present"` is the trick that keeps the lesson
  cheap.** Without it, `logfire.configure()` errors out when no token is set.
- **`logfire` is already in the sandbox passthrough list** (added by
  `PydanticAIPlugin`). You can `import logfire` at the top of a workflow module
  without extra config — but you still can't *call configuration* from inside
  the workflow body.

## Bridge

You now have all five production primitives: durable orchestration, retries,
signals, heartbeats, and traces. [Lesson 10](../10_capstone_headless/README.md)
is the capstone — a multi-agent research workflow (clarifier → researcher →
writer) with HITL approval, wired end-to-end with everything you've learned.

## Pattern

*The canonical shape, for the re-read.*

```python
import logfire
from pydantic_ai.durable_exec.temporal import LogfirePlugin
from learn_pydantic_ai import run_worker

def _configure_logfire() -> None:
    logfire.configure(send_to_logfire="if-token-present")   # no-op without LOGFIRE_TOKEN
    logfire.instrument_pydantic_ai()
    logfire.instrument_httpx(capture_all=True)

async def main() -> None:
    _configure_logfire()
    await run_worker(workflows=[ResearchWorkflow], extra_plugins=[LogfirePlugin()])
```

`LogfirePlugin` goes on the worker (`extra_plugins=`). `PydanticAIPlugin` goes
on the client (handled by `connect()`). Configure Logfire OUTSIDE workflow
code — it's non-deterministic.
