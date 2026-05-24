# Lesson 08 — Long-running activities with heartbeats

**Code:** `../examples/08_long_running/`

## Review

- In Lesson 07 you paused a workflow on a `@workflow.signal` using
  `workflow.wait_condition` — a durable, server-persisted
  human-in-the-loop pause that survived worker restarts.

## Goal

Invoke a long-running activity from a workflow and keep it alive across
the cluster's "is this worker still there?" checks via
`activity.heartbeat()`. Tune `start_to_close_timeout` and
`heartbeat_timeout` so retries fire when something genuinely dies, not
when the work just takes longer than 60 seconds.

## TL;DR

You build a plain `@activity.defn` that heartbeats in a loop, then invoke
it from the workflow with a generous `start_to_close_timeout` and a
shorter `heartbeat_timeout`. The single key mechanic is `activity.heartbeat()`:
it tells the cluster the worker is still alive so a slow-but-healthy
activity isn't killed and retried. The canonical shape is in [Pattern](#pattern).

## Why it matters

Temporal's default activity timeout is **60 seconds**. Anything slower —
a real scrape, a Whisper transcription, a Pandas pipeline, even a Claude
agent with long thinking — needs explicit timeout config + a heartbeat
loop, or the cluster decides the activity is dead and reschedules it.
That re-execution is silent failure if your activity isn't idempotent.

## Mental model

| Knob | What it bounds |
|---|---|
| `start_to_close_timeout` | One attempt. Resets on retry. |
| `heartbeat_timeout` | Max gap between heartbeats before the attempt fails. **Must be < `start_to_close_timeout`.** |
| `schedule_to_start_timeout` | How long a task may sit in the queue before a worker grabs it. |
| `schedule_to_close_timeout` | Total budget across all attempts. Default: unlimited. |

The decision tree:

```
   long-running side effect (HTTP, file IO, agent call)
                 │
   short (< 60s)?── yes ──► default timeout, no heartbeat needed
                 │
                 no
                 │
                 ▼
   set start_to_close_timeout generously
   call activity.heartbeat(...) every few seconds inside the body
   set heartbeat_timeout to roughly 2-3x the heartbeat interval
```

### Why a separate `@activity.defn` and not a pydantic-ai tool?

You CAN heartbeat from inside a pydantic-ai `@agent.tool_plain` — every
tool call already runs inside an activity that `TemporalAgent` generates,
so `temporalio.activity.heartbeat()` works from the tool body. But coupling
slow side-effecting work to a model call means every activity retry also
re-runs the LLM. Splitting them — agent picks WHAT to do, workflow body
invokes the long activity — lets each retry independently. That's the
shape this lesson teaches because it's what you'd ship.

### `continue-as-new` (briefly)

A workflow's history has a hard limit (~50k events / a few MB). For
workflows that run for months or process millions of items, use
`workflow.continue_as_new(...)` to start a fresh history with the
current state as input. Out of scope for this lesson — see
[Temporal's continue-as-new docs](https://docs.temporal.io/workflows#continue-as-new).

## Walk the code

- `examples/08_long_running/scraper.py:18` — `@activity.defn async def
  long_scrape(url)`. Plain Temporal activity, no pydantic-ai involvement.
- `examples/08_long_running/scraper.py:29` — loop sleeping 1s and calling
  `activity.heartbeat(f"chunk {i+1}/{total_seconds}")`. The positional
  arg is "details" — recoverable on the next attempt via
  `activity.heartbeat_details()` if you want resumable progress.
- `examples/08_long_running/workflows.py:80` — `workflow.execute_activity(
  long_scrape, url, start_to_close_timeout=30s, heartbeat_timeout=2s)`.
  Heartbeat budget is 2 seconds; the activity heartbeats every 1 second
  — well within the gap.
- `examples/08_long_running/worker.py:25` — `activities=[long_scrape]`
  passed to `run_worker`. PydanticAI's own activities still get
  registered automatically by the plugin.

## Run (two-terminal pattern)

```bash
# terminal A
make temporal-08-worker

# terminal B
make temporal-08
```

Open the Temporal UI while it's running. In the workflow history you
will see `ActivityTaskStarted` for `long_scrape` followed by a series of
heartbeat events — the cluster knows the worker is alive even though no
result has come back yet.

## Try it

1. **Forget to heartbeat.** Comment out the `activity.heartbeat(...)`
   call in `scraper.py`. Restart the worker, re-run. After 2 seconds the
   server kills the attempt with `ActivityTaskTimedOut` (heartbeat
   timeout) and retries automatically per the default `RetryPolicy`.
   You'll see the activity restart from the beginning in the UI.

2. **Tighten the budget.** Drop `start_to_close_timeout` to 2 seconds.
   The first attempt times out before the scrape finishes; the retry
   starts over from zero. This is what happens when you underestimate
   how long real work takes — retries are not free.

3. **Recover progress from heartbeat details.** Change the heartbeat to
   `activity.heartbeat(i + 1)` and add a check at the top of `long_scrape`:
   ```python
   start = activity.info().heartbeat_details
   resume_from = start[0] if start else 0
   ```
   Now retried attempts resume mid-way instead of re-doing work.

## Gotchas

- **`heartbeat_timeout` must be strictly less than `start_to_close_timeout`.**
  Otherwise the heartbeat check never fires before the overall attempt
  times out — heartbeats are useless.
- **Heartbeats don't reset `start_to_close_timeout`.** They only reset
  the "is the worker alive" check. If your work genuinely takes longer
  than the configured budget, raise the budget — don't heartbeat harder.
- **Activities must be idempotent or use heartbeat details.** Retries
  are a feature, not a bug; the default `RetryPolicy` will re-execute
  the whole activity on heartbeat timeout. If retrying from scratch is
  wrong (e.g. external API charges per call), use `heartbeat_details`
  to skip already-done work.
- **Workflow code cannot heartbeat.** `activity.heartbeat()` raises if
  called outside an activity. Heartbeats belong in `@activity.defn`
  bodies only — for workflow-level pauses, you'd use Lesson 07's signals
  instead.

## Bridge

You now have the four moves needed for production durable agents:
durable model calls (Lesson 03), durable tools (Lesson 04), tunable
retries (Lessons 05-06), durable pauses (Lesson 07), and durable
long-running work (Lesson 08). Lesson 09 wires Logfire into the picture
so you can correlate Temporal history with span-level traces — the
observability story that ties it all together.

## Pattern

*The canonical shape, for the re-read.*

```python
from datetime import timedelta
from temporalio import activity, workflow

@activity.defn
async def long_scrape(url: str) -> str:
    for i in range(10):
        activity.heartbeat(f"step {i}")      # tells the cluster we're alive
        await asyncio.sleep(0.5)
    return "scraped: …"

# In the workflow body:
result = await workflow.execute_activity(
    long_scrape, url,
    start_to_close_timeout=timedelta(seconds=60),
    heartbeat_timeout=timedelta(seconds=5),  # MUST be < start_to_close_timeout
)
```

Register the activity at worker startup: `run_worker(workflows=[X], activities=[long_scrape])`. For workflows that need to outlive history limits, look at `continue-as-new` (out of scope here).
