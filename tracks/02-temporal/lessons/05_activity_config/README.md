# Lesson 05 — Tuning retries & timeouts with `ActivityConfig`

> The code for this lesson is the four `.py` files in this folder. Read this
> page top to bottom; it quotes every part of the code you need to see.

## Review

In Lesson 04 you read the workflow history and watched every model call and
every tool call become its own Temporal activity. That made the activity
boundary concrete — and gave each activity a name you can now target with
config.

## Goal

Override the timeouts and retry policy for the activities pydantic-ai
auto-generates. Build a **flaky tool** that fails the first two attempts and
succeeds on the third, then *watch* the retry happen in the Temporal UI.

## Files in this lesson

| File | Role |
|---|---|
| `flaky_tool.py` | The deliberately unreliable tool. Defines `flaky_lookup`, which fails its first two calls and then succeeds. The failure logic is split out here so its counter is unambiguously activity-worker state, not workflow state. |
| `workflows.py` | Defines `LookupWorkflow`, the `@workflow.defn` class, and the `TemporalAgent` carrying the three-layer `ActivityConfig`. This is the deterministic workflow code — the thing being taught. |
| `worker.py` | The **worker process**. Registers `LookupWorkflow` and polls the task queue for work. You run it in **terminal A** and leave it running. |
| `example.py` | The **client**. Starts the workflow and prints the result. You run it in **terminal B**. |

**New this lesson:** `flaky_tool.py` — a deliberately unreliable tool/activity
that fails its first two calls so you can watch retries happen.

Temporal imposes no file or folder structure; this track splits the three
*roles* across files for the two-terminal study loop and to keep the workflow
module import-safe. Full explanation:
[Anatomy of a Temporal lesson](../../README.md#anatomy-of-a-temporal-lesson).

## How it works

A `TemporalAgent` lifts every model call and every tool call into a Temporal
activity. Each activity carries a `start_to_close_timeout` (how long a single
attempt can run) and a `RetryPolicy` (how to handle attempts that fail or time
out).

Default `ActivityConfig` is fine for greenfield demos: a 60-second timeout and
a generic retry policy. As soon as you have a tool that calls a real external
service, you need per-tool control: tight timeout for fast queries, long for
slow ones; aggressive retry for transient network errors, non-retryable for
"bad input" errors that will never succeed. This is where the durable layer
earns its keep — retries happen automatically and the workflow code stays
clean.

You stack overrides three deep:

```
activity_config            (base — applies to everything)
  └─ model_activity_config (overrides for model calls)
  └─ tool_activity_config  (per-toolset → per-tool overrides)
```

The agent's built-in function toolset — where `@agent.tool_plain` and
`@agent.tool` registrations land — has the id `'<agent>'`. That's the key to
use in the outer dict of `tool_activity_config`, which is therefore keyed
`{"<agent>": {"<tool>": {...}}}`. The per-tool dict merges over the base
`activity_config`.

Tools raise `RuntimeError` (or similar) on transient failure → Temporal catches
the activity failure → schedules a retry per the policy → the workflow keeps
going as if nothing happened. From inside the workflow, `await agent.run(...)`
either returns the final output or, eventually, raises if the policy gives up.

| LangGraph analogue | Temporal here |
|---|---|
| `with_retry` on a runnable | `RetryPolicy(maximum_attempts=...)` on an `ActivityConfig` |
| `Tool(tags={"no_retry": True})` | `non_retryable_error_types=[...]` |

## Walk the code

### `flaky_tool.py` — the deliberately unreliable tool

**`FAIL_FIRST_N`** and **`_attempts`** are module-level state living in the
**activity worker** process. Activities are normal Python; cross-call state is
fine here. Don't try this inside a workflow body — that breaks determinism.

```python
FAIL_FIRST_N = 2

# Module-level counter — survives across activity invocations within the same
# worker process. Reset by restarting the worker (or `reset_counter()` in tests).
_attempts = 0
```

**`flaky_lookup`** is the pydantic-ai tool body. It raises `RuntimeError` on
the first `FAIL_FIRST_N` calls so Temporal's retries kick in, then succeeds.

```python
async def flaky_lookup(query: str) -> str:
    global _attempts
    _attempts += 1
    _log.info("flaky_lookup attempt #%d for query=%r", _attempts, query)
    if _attempts <= FAIL_FIRST_N:
        raise RuntimeError(
            f"transient upstream error on attempt {_attempts} "
            f"(will succeed on attempt {FAIL_FIRST_N + 1})"
        )
    return f"Looked up {query!r} successfully on attempt {_attempts}."
```

**`reset_counter`** zeroes `_attempts`; it exists for the test harness, not the
lesson narrative.

### `workflows.py` — the workflow class and the agent config

**`_base`** is a plain `Agent`; `flaky_lookup` is registered onto it with
`_base.tool_plain(flaky_lookup)`, which lands it in the built-in `'<agent>'`
function toolset.

**`_flaky_tool_retry`** is the per-tool `RetryPolicy` you'll watch in the UI.
With `FAIL_FIRST_N = 2`, attempts go: 200 ms wait → fail → 400 ms wait → fail →
succeed. `non_retryable_error_types` marks exceptions that should fail fast
instead of retrying.

```python
_flaky_tool_retry = RetryPolicy(
    initial_interval=timedelta(milliseconds=200),
    backoff_coefficient=2.0,
    maximum_attempts=5,
    non_retryable_error_types=["ValueError"],
)
```

**`lookup_agent`** is the `TemporalAgent` wrapping `_base`. It carries all
three config layers. `tool_activity_config` is keyed by toolset id `'<agent>'`,
then by tool name `flaky_lookup`; what you set there merges over `activity_config`
(the base), and `model_activity_config` doesn't apply because this is a tool
call, not a model call.

```python
lookup_agent = TemporalAgent(
    _base,
    activity_config={"start_to_close_timeout": timedelta(seconds=30)},
    model_activity_config={"start_to_close_timeout": timedelta(seconds=60)},
    tool_activity_config={
        "<agent>": {
            "flaky_lookup": {
                "start_to_close_timeout": timedelta(seconds=10),
                "retry_policy": _flaky_tool_retry,
            },
        },
    },
)
```

**`LookupWorkflow.run`** is just `await lookup_agent.run(prompt)`. All the retry
machinery is in the config, not the code — tool retries happen invisibly from
the workflow's point of view.

```python
@workflow.run
async def run(self, prompt: str) -> str:
    workflow.logger.info("LookupWorkflow.run prompt=%r", prompt)
    result = await lookup_agent.run(prompt)
    return result.output
```

### `worker.py` — the worker process

One call. `run_worker` connects to the server, registers `LookupWorkflow`, and
blocks until Ctrl-C. The agent and tool activities — including all the retries
that make this lesson worth watching — run inside this process.

```python
await run_worker(workflows=[LookupWorkflow])
```

### `example.py` — the client

`execute_workflow` starts the workflow and waits for its result in one call.
The interesting bit isn't this script — it's the Temporal UI afterwards, where
you inspect the flaky tool's retry history.

```python
workflow_id = f"lesson-05-{uuid.uuid4().hex[:8]}"
result = await client.execute_workflow(
    LookupWorkflow.run,
    "Tell me about the Temporal SDK in one sentence.",
    id=workflow_id,
    task_queue=TASK_QUEUE,
)
```

## Run it

```bash
# Terminal A — server (skip if already up)
make temporal-up
make temporal-status        # should say SERVING

# Terminal A — worker (leave running)
make temporal-05-worker

# Terminal B — starter
make temporal-05
```

Then open <http://localhost:8080> → `learn-pydantic-ai` namespace → click the
workflow whose id starts with `lesson-05-...`. In the **History** tab look for
the `flaky_lookup` activity. You should see roughly:

```
ActivityTaskScheduled  (flaky_lookup, attempt 1)
ActivityTaskFailed     (RuntimeError: transient ...)
ActivityTaskScheduled  (flaky_lookup, attempt 2)
ActivityTaskFailed     (RuntimeError: transient ...)
ActivityTaskScheduled  (flaky_lookup, attempt 3)
ActivityTaskCompleted  ("Looked up '...' successfully on attempt 3.")
```

## Try it

1. **Make it fail harder.** Set `FAIL_FIRST_N = 6` in `flaky_tool.py`, restart
   the worker, re-run. The policy (`maximum_attempts=5`) gives up and the
   workflow fails. Inspect the failure event in history.
2. **Mark it non-retryable.** Change `flaky_lookup` to
   `raise ValueError("...")` instead of `RuntimeError`. Restart the worker.
   The first attempt fails and the policy refuses to retry because `ValueError`
   is in `non_retryable_error_types`.
3. **Tighten the timeout.** Drop `start_to_close_timeout` to 100 ms and add an
   `await asyncio.sleep(0.5)` inside `flaky_lookup`. You'll see
   `ActivityTaskTimedOut` events instead of `ActivityTaskFailed`.

## Gotchas

- **Toolset id is `'<agent>'`, not the tool name** at the outer dict level.
  `tool_activity_config = {"<agent>": {"flaky_lookup": {...}}}` is right;
  `tool_activity_config = {"flaky_lookup": {...}}` does nothing.
- **`ActivityConfig` is a TypedDict.** Pass dict literals, don't try to call
  `ActivityConfig(...)`.
- **`UserError` and `PydanticUserError` are auto-marked non-retryable** by
  `PydanticAIPlugin`. That's there to prevent infinite retry loops from bad
  input (a model that consistently generates a bad tool argument should fail
  loudly, not retry forever). You can add your own non-retryable types via
  `RetryPolicy.non_retryable_error_types`.
- **Bare `RuntimeError` retries by default.** The "validation failures that
  can't succeed shouldn't retry" rule is on you to enforce: raise `UserError`
  (or list your sentinel exception in `non_retryable_error_types`) for
  unrecoverable bad input. Otherwise that bad input retries up to
  `maximum_attempts` for no reason.
- **Worker process state survives across activity invocations.** The
  `_attempts` counter in `flaky_tool.py` works because the worker is one
  long-lived process; module-level globals persist between calls. That's useful
  for caches and connection pools — but DON'T rely on it for correctness: a
  deploy or crash resets that state, and a worker pool of size > 1 means
  different invocations see different copies.
- **Restart the worker** after changing `flaky_tool.py` or `workflows.py`. The
  worker doesn't hot-reload.

## Bridge

You can now tune timeouts and retries per model call and per tool, and you've
watched a transient failure ride out into a successful workflow without
touching the workflow body. [Lesson 06](../06_streaming/README.md) keeps the
workflow body as a clean `await agent.run(...)` and adds an
`event_stream_handler` so each model token and tool call streams out to a
logger, despite the deterministic workflow sandbox forbidding
`agent.run_stream()` directly.

## Pattern

*The canonical shape, for the re-read.*

```python
from datetime import timedelta
from temporalio.common import RetryPolicy

my_agent = TemporalAgent(
    _base,
    tool_activity_config={"<agent>": {"flaky_lookup": {   # outer key = toolset id
        "start_to_close_timeout": timedelta(seconds=10),
        "retry_policy": RetryPolicy(
            initial_interval=timedelta(milliseconds=200),
            maximum_attempts=5,
            non_retryable_error_types=["ValueError"],
        ),
    }}},
)
```

`ActivityConfig` is a TypedDict — pass dict literals, don't try
`ActivityConfig(...)`. `UserError` / `PydanticUserError` are auto non-retryable.
