# Lesson 04 — Workflow vs activity boundary

> The code for this lesson is the three `.py` files in this folder. Read this
> page top to bottom; it quotes every part of the code you need to see.

## Review

In Lesson 03 you wrapped a Pydantic AI `Agent` in a `TemporalAgent` +
`PydanticAIWorkflow` and ran one prompt in, one string out. With zero tools the
resulting workflow history was boring — just a model call and a result.

## Goal

Add one `@agent.tool_plain` to the Lesson 03 shape and read the resulting
workflow history. The whole point is to see — concretely, in the Temporal UI —
which lines of your code become durable activities and which stay inside the
workflow.

## Files in this lesson

| File | Role |
|---|---|
| `workflows.py` | Defines `WeatherWorkflow`, the `@workflow.defn` class, plus the `_base` agent and its one tool. The deterministic workflow code. |
| `worker.py` | The **worker process**. Registers `WeatherWorkflow` and polls the task queue. You run it in **terminal A** and leave it running. |
| `example.py` | The **client**. Starts the workflow and prints the history URL. You run it in **terminal B**. |

**Does Temporal require this three-file layout? No.** Temporal imposes no file
or folder structure — the split is this track's pedagogical choice. Full
explanation: [Anatomy of a Temporal lesson](../../README.md#anatomy-of-a-temporal-lesson).

## How it works

"Just use Temporal" is vague; "the LLM call is an activity, the tool call is an
activity, the orchestration is the workflow" is operational. Once you can point
at the history events that prove this, every later configuration knob
(timeouts, retry policies, heartbeats) has an obvious target.

Here you add a single `@agent.tool_plain` to the bare agent from Lesson 03 and
inspect the resulting workflow history. The key mechanic: `TemporalAgent` lifts
*both* the model call and the tool call into their own durable activities, so a
single agent run with one tool invocation produces three activity pairs in
history.

The rule, memorized:

- **Model calls = activity.** Each `model_request` is lifted into its own
  activity by `TemporalAgent`.
- **Tool calls = activity.** Each `@agent.tool` / `@agent.tool_plain` becomes
  its own activity, named after the tool.
- **Orchestration = workflow.** The `@workflow.run` body itself contributes
  `WorkflowTaskCompleted` events between activity calls — it's the deterministic
  glue that decides what to schedule next.

For a single agent call with one tool invocation, expect three activity pairs
in history:

```
ActivityTaskScheduled / ActivityTaskCompleted   -- model_request   (decides: call get_weather)
ActivityTaskScheduled / ActivityTaskCompleted   -- get_weather     (returns "rainy, 12C")
ActivityTaskScheduled / ActivityTaskCompleted   -- model_request   (turns the result into prose)
WorkflowExecutionCompleted
```

### Two ways an activity gets scheduled

Notice you did **not** write `workflow.execute_activity(...)` anywhere — yet
three activities ran. That's the difference between Lesson 01 and the agent
lessons:

- **Explicit** (Lesson 01): you call `await workflow.execute_activity(say_hello, ...)`
  by hand. You choose what becomes an activity.
- **Implicit** (here): `TemporalAgent` lifts every model request and every
  `@agent.tool` call into an activity for you. The `await agent.run(prompt)`
  line schedules all of them — you never name them.

Both produce identical history events; the only difference is who writes the
`execute_activity` call. You'll go back to the **explicit** form in Lesson 08,
where a long-running scrape is your own `@activity.defn` invoked by hand from
the workflow body — work that isn't a model or tool call, so the wrapper won't
lift it for you.

## Coming from LangGraph?

The full translation table lives in
[Lesson 03](../03_hello_durable/README.md#coming-from-langgraph). One addition
for this lesson: a `@agent.tool` is the analogue of a checkpointed sub-node —
its return value is memoized and never re-computed on replay. That's why
side-effecting tools (HTTP calls, DB writes) belong here and not in the
workflow body.

## Walk the code

### `workflows.py` — the agent, its tool, and the workflow class

**`_WEATHER`** is a hardcoded weather table. The tool returns deterministic
strings so the lesson always produces a clean, readable history — no real
network involved.

```python
_WEATHER: dict[str, str] = {
    "london": "rainy, 12C",
    "tokyo": "sunny, 22C",
    "san francisco": "foggy, 15C",
}
```

**`get_weather`** is registered with `@_base.tool_plain`. It's `tool_plain`
because the tool needs nothing from `RunContext`. The docstring is what the
model reads to decide when to call it.

```python
@_base.tool_plain
def get_weather(city: str) -> str:
    """Return current weather for `city`. Returns a short status string."""
    return _WEATHER.get(city.lower(), f"no data for {city}")
```

**`weather_agent = TemporalAgent(_base)`** is created *after* the tool is
registered. The wrapper inspects the agent's toolset at construction time;
tools added later won't be lifted into activities.

```python
weather_agent = TemporalAgent(_base)
```

**`WeatherWorkflow.run`** uses `workflow.logger.info(...)` instead of `print()`.
The workflow sandbox replays this code; loggers are replay-safe, `print` is not.
The single `await weather_agent.run(...)` line schedules all three activities.

```python
@workflow.run
async def run(self, city: str) -> str:
    workflow.logger.info("WeatherWorkflow running for city=%s", city)
    result = await weather_agent.run(f"What's the weather in {city}?")
    return result.output
```

### `worker.py` — the worker process

One call. `run_worker` connects to the server and registers `WeatherWorkflow`.
Because the agent's `@tool_plain` is reachable via `__pydantic_ai_agents__`,
`PydanticAIPlugin` registers the tool's auto-generated activity for you — no
manual `activities=[get_weather]` needed.

```python
await run_worker(workflows=[WeatherWorkflow])
```

### `example.py` — the client

`client.execute_workflow` starts the workflow and awaits its result. Same
starter shape as Lesson 03; only the workflow class and argument differ. The
printed URL is where you'll inspect the activity boundary.

```python
result = await client.execute_workflow(
    WeatherWorkflow.run,
    "London",
    id=workflow_id,
    task_queue=TASK_QUEUE,
)
```

## Run it

Server up (`make temporal-up`, leave running), then two terminals:

```bash
# Terminal A — worker (Ctrl-C to stop)
make temporal-04-worker
```

```bash
# Terminal B — starter
make temporal-04
```

Then open the printed history URL. In the UI's "History" tab, switch to
"Compact" view and look for three blocks of `ActivityTaskScheduled` /
`ActivityTaskCompleted`. The middle one is `get_weather`. The first and third
are `model_request`.

## Try it

1. **Add a second tool.** `get_time(tz: str) -> str` returning a hardcoded
   string. Ask the agent "What's the time and weather in Tokyo?" Re-run; observe
   that history now contains *four* activity pairs (two model requests, two tool
   calls).
2. **Make the tool fail.** Inside `get_weather`, `raise RuntimeError("api down")`
   for the city `"failtown"`. Run with `"failtown"`. Watch the UI: the activity
   gets retried per the default `RetryPolicy` before the workflow gives up.
3. **Move work into the workflow body and watch it break.** Try
   `import random; random.randint(0, 5)` inside `@workflow.run`. The sandbox
   refuses to execute it — that's determinism enforcement.

## Gotchas

- **Register tools BEFORE wrapping.** `TemporalAgent(_base)` reads `_base.tools`
  at construction. If you add `@_base.tool_plain` after the wrap, that tool is
  invisible to Temporal.
- **`tool_plain` vs `tool`.** No `RunContext` parameter → `tool_plain`. With
  one → `tool`. Mixing them raises at runtime, just like in Track 01.
- **Tool docstrings are part of the prompt.** A vague docstring makes the model
  skip the tool. Write them as user-facing instructions.
- **No `httpx.get()` inside `@workflow.run`.** Even if it's "just" reading a
  config, the sandbox blocks it. Put it in a tool or a custom `@activity.defn`.
- **Module-level side effects break replay.** The sandbox re-imports
  `workflows.py` to reconstruct workflow state from history. If your module does
  `open("config.json")` or `requests.get(...)` at import time, that I/O happens
  on the first run but not on replay — the workflow then diverges from its
  recorded history. Keep import-time work pure; defer I/O to activities or tool
  bodies. The reason `learn_pydantic_ai` is registered as a sandbox passthrough
  is that it deliberately reads `.env` at import — passing through reuses the
  already-loaded module instead of re-running its imports.
- **Activity name = `agent_name__tool_name`.** Visible in the UI under "Activity
  Type". Useful when you want per-tool retry config later (Lesson 05).

## Bridge

You can now see the boundary — which lines of your code become durable
activities and which stay inside the workflow.
[Lesson 05](../05_activity_config/README.md) makes it tunable — per-tool
timeouts, retry policies, and the `ActivityConfig` knob that controls all of it.

## Pattern

*The canonical shape, for the re-read.*

```python
_base = Agent(model=FLASH, name="weather_agent", instructions="…")

@_base.tool_plain                  # register tools BEFORE wrapping
def get_weather(city: str) -> str:
    return _WEATHER.get(city.lower(), "no data")

weather_agent = TemporalAgent(_base)   # wrap AFTER tools are registered
```

Resulting workflow history: `model_request` activity → `get_weather` activity →
`model_request` activity → done. **Both** the LLM call AND the tool call become
activities.
