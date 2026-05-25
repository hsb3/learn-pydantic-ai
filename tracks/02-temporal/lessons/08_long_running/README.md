# Lesson 08 — Long-running activities with heartbeats

> The code for this lesson is the four `.py` files in this folder. Read this
> page top to bottom; it quotes every part of the code you need to see.

## Review

In Lesson 07 you paused a workflow on a `@workflow.signal` using
`workflow.wait_condition` — a durable, server-persisted human-in-the-loop pause
that survived worker restarts.

## Goal

Invoke a long-running activity from a workflow and keep it alive across the
cluster's "is this worker still there?" checks via `activity.heartbeat()`. Tune
`start_to_close_timeout` and `heartbeat_timeout` so retries fire when something
genuinely dies, not when the work just takes longer than 60 seconds.

## Files in this lesson

| File | Role |
|---|---|
| `workflows.py` | Defines `LongScrapeWorkflow`, the `@workflow.defn` class. An agent picks a URL, then the workflow body invokes the long activity. The deterministic code being taught. |
| `worker.py` | The **worker process**. Registers `LongScrapeWorkflow` *and* the custom `long_scrape` activity, then polls the task queue. You run it in **terminal A** and leave it running. |
| `example.py` | The **client**. Starts the workflow and waits for the result. You run it in **terminal B**. |
| `scraper.py` | The long-running activity, `long_scrape`. |

**New this lesson:** `scraper.py` — a plain `@activity.defn` (no pydantic-ai)
that simulates slow work and heartbeats in a loop. It is the first lesson where
the worker registers a *custom* activity alongside its workflow, via
`activities=[long_scrape]`. (Temporal imposes no file layout; this track splits
the roles into files for the two-terminal study loop and to keep the workflow
module import-safe — full explanation:
[Anatomy of a Temporal lesson](../../README.md#anatomy-of-a-temporal-lesson).)

## How it works

Temporal's default activity timeout is **60 seconds**. Anything slower — a real
scrape, a Whisper transcription, a Pandas pipeline, even a Claude agent with
long thinking — needs explicit timeout config plus a heartbeat loop, or the
cluster decides the activity is dead and reschedules it. That re-execution is
silent failure if your activity isn't idempotent.

So you build a plain `@activity.defn` that heartbeats in a loop, then invoke it
from the workflow with a generous `start_to_close_timeout` and a shorter
`heartbeat_timeout`. The single key mechanic is `activity.heartbeat()`: it tells
the cluster the worker is still alive so a slow-but-healthy activity isn't
killed and retried. The canonical shape is in [Pattern](#pattern).

Four timeout knobs govern the activity:

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

You CAN heartbeat from inside a pydantic-ai `@agent.tool_plain` — every tool
call already runs inside an activity that `TemporalAgent` generates, so
`temporalio.activity.heartbeat()` works from the tool body. But coupling slow
side-effecting work to a model call means every activity retry also re-runs the
LLM. Splitting them — agent picks WHAT to do, workflow body invokes the long
activity — lets each retry independently. That's the shape this lesson teaches
because it's what you'd ship.

### `continue_as_new` — the long-horizon escape hatch

A workflow's history has a hard cap (~50,000 events / a few MB). Once a workflow
crosses that, the server refuses to record more — your workflow can't make
progress. That doesn't affect short scrapes like this one, but a workflow that
runs for weeks (polling a queue, processing a long stream, monitoring something)
will hit the wall eventually.

The fix is `workflow.continue_as_new(...)`. It atomically:

1. Closes the current workflow execution with **status `CONTINUED_AS_NEW`**
2. Starts a fresh execution under the **same workflow ID**, passing whatever
   state you give it as the new input

The new execution gets an empty history; the old one's history can be archived.
Callers `await handle.result()` transparently — Temporal follows the
continue-as-new chain to the final execution and returns its result.

Wrapping `LongScrapeWorkflow` to roll over every N iterations looks like this:

```python
@workflow.defn
class LongScrapeLoopWorkflow(PydanticAIWorkflow):
    """Scrape a stream of topics; continue-as-new every 100 iterations."""

    __pydantic_ai_agents__ = [url_agent]

    @workflow.run
    async def run(self, topics: list[str], iteration: int = 0) -> str:
        BATCH = 100
        for i in range(BATCH):
            if not topics:
                return f"done after {iteration + i} iterations"
            topic = topics.pop(0)
            await self._scrape_one(topic)
        # History is getting long — hand off to a fresh execution.
        workflow.continue_as_new(args=[topics, iteration + BATCH])
```

`continue_as_new(...)` doesn't return — it raises `_NewWorkflowSourceContinuedAsNew`
which Temporal catches at the workflow boundary. Anything after the call is
unreachable (and the type checker will complain if you use `args=` plus typed
return). Pass forward **only** the state the new execution needs; that's the
discipline ralph-wiggum's README calls out as the "essential state" rule.

It's not part of this lesson's runnable code — the scrape workflow finishes in
seconds and never approaches the history limit — but it's the answer when
someone asks "what happens when a workflow runs for months?"

## Walk the code

### `scraper.py` — the long-running activity

**`long_scrape`** is a plain `@activity.defn` — no pydantic-ai involvement. It
simulates a 4-second scrape and heartbeats once per second so Temporal knows the
worker is alive even though no result has come back yet. In a real activity this
body would call `httpx.get()` or kick off a Playwright session; the
side-effecting call is what makes it activity code and not workflow code.

```python
@activity.defn
async def long_scrape(url: str) -> str:
    activity.logger.info("long_scrape starting url=%s", url)

    total_seconds = 4
    for i in range(total_seconds):
        await asyncio.sleep(1)
        activity.heartbeat(f"chunk {i + 1}/{total_seconds}")
        activity.logger.info("long_scrape heartbeat %d/%d", i + 1, total_seconds)

    return f"[scraped {url}: lorem ipsum dolor sit amet]"
```

`activity.heartbeat(...)` is the "I'm still alive" ping. Without it, Temporal
considers the activity dead once `heartbeat_timeout` elapses with no contact and
re-schedules the whole activity on another worker. The optional positional arg
is "details" — anything pickleable, preserved across restarts via
`activity.heartbeat_details()` if you want resumable progress.

### `workflows.py` — the workflow class

**`LongScrapeWorkflow`** is a `PydanticAIWorkflow` subclass that lists one agent,
`url_agent` (a `TemporalAgent` wrapping a regular pydantic-ai `Agent`), in
`__pydantic_ai_agents__`.

```python
@workflow.defn
class LongScrapeWorkflow(PydanticAIWorkflow):
    """One agent pick + one long-running activity, with heartbeats."""

    __pydantic_ai_agents__ = [url_agent]
```

**`LongScrapeWorkflow.run`** orchestrates both halves. First the agent picks one
URL from `_CANDIDATES` — fast, deterministic-shaped work that benefits from
activity retry semantics:

```python
pick = await url_agent.run(prompt)
url = pick.output.strip()
```

Then the workflow body invokes `long_scrape` directly via
`workflow.execute_activity`. The heartbeat budget is 2 seconds and the activity
heartbeats every 1 second — well within the gap:

```python
scraped = await workflow.execute_activity(
    long_scrape,
    url,
    start_to_close_timeout=timedelta(seconds=30),
    heartbeat_timeout=timedelta(seconds=2),
)
```

`start_to_close_timeout` budgets a single attempt; if the worker stops
heartbeating for longer than `heartbeat_timeout`, Temporal gives up on this
attempt and retries. Each half is durable on its own — if `long_scrape` fails
halfway, only it retries; the agent's pick is already memoized in workflow
history.

### `worker.py` — the worker process

This is the first lesson where the worker registers a **custom activity**
alongside its workflow. `long_scrape` is passed via `activities=[long_scrape]`
so the worker picks up activity tasks for it from the task queue. PydanticAI's
auto-generated activities (model calls, tool calls) are still installed by
`PydanticAIPlugin` — no change there.

```python
await run_worker(workflows=[LongScrapeWorkflow], activities=[long_scrape])
```

### `example.py` — the client

`execute_workflow` starts the workflow and blocks until the result comes back.
Total wall-clock time is ~4–6 seconds: a fast LLM pick plus the ~4-second
simulated scrape.

```python
result = await client.execute_workflow(
    LongScrapeWorkflow.run,
    "Temporal durable execution basics",
    id=workflow_id,
    task_queue=TASK_QUEUE,
)
```

## Run it

Server up first (`make temporal-up`, leave running), then two terminals:

```bash
# Terminal A — worker (Ctrl-C to stop)
make temporal-08-worker
```

```bash
# Terminal B — starter
make temporal-08
```

Open the Temporal UI while it's running. In the workflow history you will see
`ActivityTaskStarted` for `long_scrape` followed by a series of heartbeat events
— the cluster knows the worker is alive even though no result has come back yet.

## Try it

1. **Forget to heartbeat.** Comment out the `activity.heartbeat(...)` call in
   `scraper.py`. Restart the worker, re-run. After 2 seconds the server kills
   the attempt with `ActivityTaskTimedOut` (heartbeat timeout) and retries
   automatically per the default `RetryPolicy`. You'll see the activity restart
   from the beginning in the UI.

2. **Tighten the budget.** Drop `start_to_close_timeout` to 2 seconds. The first
   attempt times out before the scrape finishes; the retry starts over from
   zero. This is what happens when you underestimate how long real work takes —
   retries are not free.

3. **Recover progress from heartbeat details.** Change the heartbeat to
   `activity.heartbeat(i + 1)` and add a check at the top of `long_scrape`:
   ```python
   start = activity.info().heartbeat_details
   resume_from = start[0] if start else 0
   ```
   Now retried attempts resume mid-way instead of re-doing work.

4. **Continue-as-new in action.** Add a new workflow in `workflows.py`:
   ```python
   @workflow.defn
   class IterateWorkflow:
       @workflow.run
       async def run(self, iteration: int = 0) -> int:
           workflow.logger.info("iteration=%d", iteration)
           if iteration >= 3:
               return iteration
           workflow.continue_as_new(args=[iteration + 1])
   ```
   Register it with `workflows=[LongScrapeWorkflow, IterateWorkflow]` in
   `worker.py`, then start it from a one-off script. In the UI you'll see
   four executions linked by the **continued-as-new** relationship,
   each with the next iteration as its input. `handle.result()` follows
   the chain and returns `3`.

## Gotchas

- **`heartbeat_timeout` must be strictly less than `start_to_close_timeout`.**
  Otherwise the heartbeat check never fires before the overall attempt times out
  — heartbeats are useless.
- **Heartbeats don't reset `start_to_close_timeout`.** They only reset the "is
  the worker alive" check. If your work genuinely takes longer than the
  configured budget, raise the budget — don't heartbeat harder.
- **Activities must be idempotent or use heartbeat details.** Retries are a
  feature, not a bug; the default `RetryPolicy` will re-execute the whole
  activity on heartbeat timeout. If retrying from scratch is wrong (e.g. an
  external API charges per call), use `heartbeat_details` to skip already-done
  work.
- **Workflow code cannot heartbeat.** `activity.heartbeat()` raises if called
  outside an activity. Heartbeats belong in `@activity.defn` bodies only — for
  workflow-level pauses, you'd use Lesson 07's signals instead.
- **`continue_as_new(...)` doesn't return.** It raises an internal exception
  Temporal catches at the workflow boundary. Nothing after the call runs;
  putting code there is dead. Hand off ONLY the state the next execution needs
  — `continue_as_new` is for shedding history weight, not for hoisting old
  state along for the ride.

## Bridge

You now have the moves needed for production durable agents: durable model calls
(Lesson 03), durable tools (Lesson 04), tunable retries (Lessons 05–06), durable
pauses (Lesson 07), and durable long-running work (this lesson).
[Lesson 09](../09_observability/README.md) wires Logfire into the picture so you
can correlate Temporal history with span-level traces — the observability story
that ties it all together.

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

Register the activity at worker startup:
`run_worker(workflows=[X], activities=[long_scrape])`. For workflows that need
to outlive Temporal's per-execution history limit (~50k events), shed weight by
calling `workflow.continue_as_new(args=[...])` — same workflow ID, fresh
execution, passes forward only the state you specify.
```
