# Lesson 05 — Tuning retries & timeouts with `ActivityConfig`

**Code:** `../examples/05_activity_config/`

## Review

- In Lesson 04 you read the workflow history and watched every model call and every tool call become its own Temporal activity.
- That made the activity boundary concrete — and gave each activity a name you can now target with config.

## Goal

Override the timeouts and retry policy for the activities pydantic-ai
auto-generates. Build a **flaky tool** that fails the first two attempts and
succeeds on the third, then *watch* the retry happen in the Temporal UI.

## TL;DR

Here you override the auto-generated activities' timeouts and retry policy with `ActivityConfig`, building a flaky tool that fails twice then succeeds so you can watch the retries unfold in the Temporal UI. The key mechanic: `tool_activity_config` is keyed `{"<agent>": {"<tool>": {...}}}`, where `'<agent>'` is the built-in function toolset id and the per-tool dict merges over the base config. The canonical shape is in [Pattern](#pattern).

## Why it matters

Default `ActivityConfig` is fine for greenfield demos: a 60-second timeout
and a generic retry policy. As soon as you have a tool that calls a real
external service, you need per-tool control: tight timeout for fast queries,
long for slow ones; aggressive retry for transient network errors,
non-retryable for "bad input" errors that will never succeed. This is where
the durable layer earns its keep — retries happen automatically and the
workflow code stays clean.

## Mental model

A `TemporalAgent` lifts every model call and every tool call into a Temporal
activity. Each activity carries a `start_to_close_timeout` (how long a
single attempt can run) and a `RetryPolicy` (how to handle attempts that
fail or time out).

You stack overrides three deep:

```
activity_config            (base — applies to everything)
  └─ model_activity_config (overrides for model calls)
  └─ tool_activity_config  (per-toolset → per-tool overrides)
```

The agent's built-in function toolset — where `@agent.tool_plain` and
`@agent.tool` registrations land — has the id `'<agent>'`. That's the
key to use in the outer dict of `tool_activity_config`.

Tools raise `RuntimeError` (or similar) on transient failure → Temporal
catches the activity failure → schedules a retry per the policy → the
workflow keeps going as if nothing happened. From inside the workflow,
`await agent.run(...)` either returns the final output or, eventually,
raises if the policy gives up.

| LangGraph analogue | Temporal here |
|---|---|
| `with_retry` on a runnable | `RetryPolicy(maximum_attempts=...)` on an `ActivityConfig` |
| `Tool(tags={"no_retry": True})` | `non_retryable_error_types=[...]` |

## Walk the code

- `flaky_tool.py:36` — `_attempts` is a module-level counter living in the
  **activity worker** process. Activities are normal Python; cross-call
  state is fine here. Don't try this inside a workflow body — that breaks
  determinism.
- `flaky_tool.py:46` — `flaky_lookup` raises `RuntimeError` on the first
  `FAIL_FIRST_N` calls so Temporal retries kick in.
- `workflows.py:42` — `RetryPolicy(initial_interval=200ms, backoff_coefficient=2,
  maximum_attempts=5, non_retryable_error_types=["ValueError"])`. With
  `FAIL_FIRST_N=2`, attempts go: 200ms wait → fail → 400ms wait → fail →
  succeed.
- `workflows.py:55` — `tool_activity_config={"<agent>": {"flaky_lookup": {...}}}`
  is the per-tool override. Anything you set here merges over
  `activity_config` (base) and `model_activity_config` doesn't apply
  because this is a tool call, not a model call.
- `workflows.py:74` — workflow body is just `await agent.run(prompt)`. All
  the retry machinery is in the config, not the code.

## Run

```bash
# Terminal A — server (skip if already up)
make temporal-up
make temporal-status        # should say SERVING

# Terminal A — worker (leave running)
make temporal-05-worker

# Terminal B — starter
make temporal-05
```

Then open <http://localhost:8080> → `learn-pydantic-ai` namespace → click
the workflow whose id starts with `lesson-05-...`. In the **History** tab
look for the `flaky_lookup` activity. You should see roughly:

```
ActivityTaskScheduled  (flaky_lookup, attempt 1)
ActivityTaskFailed     (RuntimeError: transient ...)
ActivityTaskScheduled  (flaky_lookup, attempt 2)
ActivityTaskFailed     (RuntimeError: transient ...)
ActivityTaskScheduled  (flaky_lookup, attempt 3)
ActivityTaskCompleted  ("Looked up '...' successfully on attempt 3.")
```

## Try it

1. **Make it fail harder.** Set `FAIL_FIRST_N = 6` in `flaky_tool.py`,
   restart the worker, re-run. The policy (`maximum_attempts=5`) gives up
   and the workflow fails. Inspect the failure event in history.
2. **Mark it non-retryable.** Change `flaky_lookup` to
   `raise ValueError("...")` instead of `RuntimeError`. Restart the worker.
   The first attempt fails and the policy refuses to retry because
   `ValueError` is in `non_retryable_error_types`.
3. **Tighten the timeout.** Drop `start_to_close_timeout` to 100ms and
   add an `await asyncio.sleep(0.5)` inside `flaky_lookup`. You'll see
   `ActivityTaskTimedOut` events instead of `ActivityTaskFailed`.

## Gotchas

- **Toolset id is `'<agent>'`, not the tool name** at the outer dict level.
  `tool_activity_config = {"<agent>": {"flaky_lookup": {...}}}` is right;
  `tool_activity_config = {"flaky_lookup": {...}}` does nothing.
- **`ActivityConfig` is a TypedDict.** Pass dict literals, don't try to
  call `ActivityConfig(...)`.
- **`UserError` and `PydanticUserError` are auto-marked non-retryable** by
  `PydanticAIPlugin`. That's there to prevent infinite retry loops from
  bad input (a model that consistently generates a bad tool argument
  should fail loudly, not retry forever). You can add your own
  non-retryable types via `RetryPolicy.non_retryable_error_types`.
- **Bare `RuntimeError` retries by default.** The "validation failures
  that can't succeed shouldn't retry" rule is on you to enforce: raise
  `UserError` (or list your sentinel exception in `non_retryable_error_types`)
  for unrecoverable bad input. Otherwise that bad input retries up to
  `maximum_attempts` for no reason.
- **Worker process state survives across activity invocations.** The
  `_attempts` counter in `flaky_tool.py` works because the worker is one
  long-lived process; module-level globals persist between calls. That's
  useful for caches and connection pools — but DON'T rely on it for
  correctness: a deploy or crash resets that state, and a worker pool of
  size > 1 means different invocations see different copies.
- **Restart the worker** after changing `flaky_tool.py` or `workflows.py`.
  The worker doesn't hot-reload.

## Bridge

Lesson 06 keeps the workflow body as a clean `await agent.run(...)` and
adds an `event_stream_handler` so each model token / tool call streams
out to a logger, despite the deterministic workflow sandbox forbidding
`agent.run_stream()` directly.

## Pattern

*The canonical shape, for the re-read.*

```python
from datetime import timedelta
from temporalio.common import RetryPolicy

my_agent = TemporalAgent(
    _base,
    tool_activity_config={"<agent>": {"flaky_lookup": {   # outer key = agent name
        "start_to_close_timeout": timedelta(seconds=10),
        "retry_policy": RetryPolicy(
            initial_interval=timedelta(milliseconds=200),
            maximum_attempts=5,
            non_retryable_error_types=["ValueError"],
        ),
    }}},
)
```

`ActivityConfig` is a TypedDict — pass dict literals, don't try `ActivityConfig(...)`. `UserError` / `PydanticUserError` are auto non-retryable.
