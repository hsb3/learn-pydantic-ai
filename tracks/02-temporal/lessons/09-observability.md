# Lesson 09 — Observability with Logfire

**Code:** `../examples/09_observability/`

## Review

- In Lesson 08 you kept a long-running activity alive across the
  cluster's liveness checks with `activity.heartbeat()` and tuned
  `start_to_close_timeout` / `heartbeat_timeout` so retries only fired
  on genuine death.

## Goal
Wire `LogfirePlugin` into a Temporal worker so every workflow execution becomes a Logfire trace — with model requests, tool calls, and even the underlying HTTP calls as nested spans.

## TL;DR
You add `LogfirePlugin` to the worker's `extra_plugins=` and call
`logfire.configure()` once at startup, instrumenting pydantic-ai and httpx.
The single key mechanic is that the Logfire wiring lives OUTSIDE the
workflow body — configuration is non-deterministic, so it happens at
worker boot while the plugin handles per-execution tracing. The canonical shape is in [Pattern](#pattern).

## Why it matters
The Temporal UI shows you *workflow history* — every activity scheduled, started, completed, retried. It does **not** show you what the agent was actually *thinking*: token usage, structured-output parsing, the exact JSON sent to the model. Logfire fills that gap. Wire both, and you get end-to-end correlation: click a workflow in Temporal → jump to its Logfire trace → drill into the LLM call that took 6 seconds.

## Mental model

One `ResearchWorkflow` execution becomes a trace tree like this:

```
Workflow span  [ResearchWorkflow]
├── Activity span  [researcher__model_request]
│   └── HTTP span  POST generativelanguage.googleapis.com/...
├── Activity span  [researcher__look_up_population]
├── Activity span  [researcher__look_up_currency]
└── Activity span  [researcher__model_request]
    └── HTTP span  POST generativelanguage.googleapis.com/...
```

`LogfirePlugin` registers Temporal's OpenTelemetry tracing interceptor, so the *workflow* and *activity* spans come for free. `logfire.instrument_pydantic_ai()` adds the *Agent.run* + tool-call spans inside each activity. `logfire.instrument_httpx(capture_all=True)` adds the HTTP spans inside each model-request span.

## Walk the code
- `workflows.py` — a standard `PydanticAIWorkflow` with two tools. Nothing here knows about Logfire. The workflow stays portable and deterministic.
- `worker.py:43` — `logfire.configure(send_to_logfire="if-token-present", ...)`. Called BEFORE `run_worker(...)`. Graceful no-op when no token is present.
- `worker.py:53` — `logfire.instrument_pydantic_ai()` and `logfire.instrument_httpx(capture_all=True)` — the two extra layers of detail.
- `worker.py:65` — `extra_plugins=[LogfirePlugin()]` — appended to `PydanticAIPlugin()` inside `run_worker`, so plugin order is `[PydanticAIPlugin(), LogfirePlugin()]`. Order matters: `PydanticAIPlugin` must come first to register activities; `LogfirePlugin` then wraps everything with tracing.

Why is the Logfire setup in `worker.py` and not `workflows.py`? Workflow bodies must be deterministic — re-runnable from history without side effects. `logfire.configure()` opens an OTel exporter, reads env vars, and writes to disk: all forbidden inside a workflow sandbox. Configure once at worker startup; the plugin handles the per-execution wiring.

## Run
Two terminals. Same pattern as every other lesson:

```bash
# Terminal A
make temporal-09-worker

# Terminal B
make temporal-09
```

Without `LOGFIRE_TOKEN` you'll see the worker print `LOGFIRE_TOKEN not set — running in no-op mode`. The workflow still runs to completion; you just don't get the shipped traces. Open `http://localhost:8080` and click your workflow to see the standard Temporal history.

With `LOGFIRE_TOKEN=...` in `.env`, you'll see the worker print a `https://logfire.pydantic.dev` URL. Click into the trace there — the same workflow now has spans for every model call and every HTTP request.

## Try it
1. Sign up for a free Logfire account → create a write token → put `LOGFIRE_TOKEN=...` in `.env` → restart the worker → re-run. Open the printed URL.
2. Change `look_up_population` to `raise RuntimeError("simulated outage")`. Re-run. Compare what the *Temporal UI* shows (the activity went into retry) vs what *Logfire* shows (the exception span with stack trace).
3. Crank up the question complexity: `"For each of Tokyo, Paris, and São Paulo, give me the population and currency."` Watch the trace tree get deeper — more model requests, more tool calls.

## Coming from langgraph-api?
Traces in LangSmith for a langgraph-api app map roughly 1:1 to traces in Logfire here — same idea, same span tree, same drill-down ergonomics. The difference is that Temporal also gives you the *workflow-history* view at `localhost:8080`, which is finer-grained than LangSmith: every signal, every retry, every timer is an event in history, not just a span. You end up with two complementary views — Temporal for "what did the durable runtime do?", Logfire for "what was the LLM thinking?".

## Gotchas
- **Never call `logfire.configure()` inside `@workflow.run`.** Configure once in the worker process before `run_worker(...)`. Logfire spans emitted from inside an activity are fine — the activity is normal Python, not sandboxed workflow code.
- **`LogfirePlugin` must come AFTER `PydanticAIPlugin` in the plugin list.** `run_worker` already prepends `PydanticAIPlugin`, so passing it via `extra_plugins=` is correct.
- **`send_to_logfire="if-token-present"` is the trick that keeps the lesson cheap.** Without it, `logfire.configure()` errors out when no token is set.
- **`logfire` is already in the sandbox passthrough list** (added by `PydanticAIPlugin`). You can `import logfire` at the top of a workflow module without extra config — but you still can't *call configuration* from inside the workflow body.

## Bridge
You now have all five production primitives: durable orchestration, retries, signals, heartbeats, and traces. Lesson 10 is the capstone — a multi-agent research workflow (clarifier → researcher → writer) with HITL approval, wired end-to-end with everything you've learned.

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

`LogfirePlugin` goes on the worker (`extra_plugins=`). `PydanticAIPlugin` goes on the client (handled by `connect()`). Configure Logfire OUTSIDE workflow code — it's non-deterministic.
