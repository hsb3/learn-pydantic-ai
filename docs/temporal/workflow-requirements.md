# What Temporal needs from your code

A reference for the irreducible parts of a Temporal app — server, client, worker, workflow code, activities — and what each piece must look like for the cluster to do its job.

> **TL;DR** — Four things have to exist and reach each other: a **server** (the cluster), a **client** (process that submits work), a **worker** (process that does work), and the **workflow code** (a deterministic Python class). The server enforces a determinism contract on workflow code; everything that does I/O or wall-clock work gets pushed out into **activities** that the server orchestrates with retries, timeouts, and heartbeats.

## The four collaborators

```
┌────────┐  schedule   ┌─────────┐ poll/ack ┌────────┐
│ Client │ ──────────► │ Server  │ ◄─────── │ Worker │
└────────┘   result    └─────────┘  task    └────────┘
                            │                    │
                            │ workflow history   │ executes
                            │ (the truth)        │ workflow + activities
                            ▼                    ▼
                       ┌──────────┐       ┌──────────────┐
                       │ Storage  │       │ Your Python  │
                       └──────────┘       └──────────────┘
```

| Component | What it is | Where it runs |
|---|---|---|
| **Server** (cluster) | Postgres + frontend gRPC + matching + history services. Stores every event. | Docker compose / Temporal Cloud / self-hosted. |
| **Client** | Process that calls `start_workflow` / `execute_workflow` / `signal` / `query`. | Anywhere — a CLI, a FastAPI handler, a notebook. |
| **Worker** | Long-lived process that polls a task queue. Has your workflows and activities registered on it. | A box / container *you* run. The cluster never executes your code. |
| **Workflow code** | A Python class `@workflow.defn` with one `@workflow.run` method. Deterministic. | Imported by the worker; runs inside the worker's sandbox. |

The cluster never sees your code, just events. Workers do the work; clients submit requests; the server keeps the authoritative history.

## Minimum viable workflow

```python
from temporalio import workflow

@workflow.defn
class MinimalWorkflow:
    @workflow.run
    async def run(self, name: str) -> str:
        return f"hello {name}"
```

The irreducible bits:

1. **`@workflow.defn`** on the class — the registry marker.
2. **Exactly one `@workflow.run`** async method — the entry point. Its signature is the workflow's public API.
3. **Class state lives on `self`** — initialized in `__init__` (which runs on every start *and* every replay).
4. **JSON-serializable args + return** — pydantic-ai's plugin handles pydantic models for you; otherwise stick to primitives, dataclasses, or Pydantic models with the pydantic data converter.

Track 02's [Lesson 02](../../tracks/02-temporal/lessons/02_stateful_workflow/README.md) is this skeleton plus a signal handler.

## The determinism contract

Workflow code re-runs from history during recovery and during normal task processing. Every replay must produce the same sequence of decisions, or the workflow will fail with a non-determinism error. That means:

| ✗ Forbidden in workflow code | ✓ Use instead |
|---|---|
| `time.time()`, `datetime.now()` | `workflow.now()` |
| `random.random()` | `workflow.random()` |
| `asyncio.sleep(n)` | `workflow.sleep(n)` |
| `requests.get(...)` / `httpx.AsyncClient` | An activity |
| File I/O | An activity |
| `os.environ` / global state reads | Pass via args, or an activity |
| `print(...)` / stdlib `logging` | `workflow.logger` |
| Blocking calls (`time.sleep`, blocking DB drivers) | An activity (or an async equivalent) |

`asyncio.gather` / `create_task` work inside a workflow — Temporal patches asyncio so the wrapped coroutines run under its deterministic scheduler. The trick is that *anything they await* still has to obey this contract.

The sandbox imports your workflow modules *fresh* on every worker startup and partially on replay. Anything that runs at module import time gets re-run. **Workflow modules must be import-safe** — no top-level network calls, no env-var reads that crash if missing, no file I/O. This is the single most common gotcha; it's why this repo's `learn_pydantic_ai` package is added to the sandbox passthrough list ([`learn_pydantic_ai/temporal.py`](../../learn_pydantic_ai/temporal.py)).

## Activities — the I/O safe zone

Anything that touches the world goes in an activity:

```python
from temporalio import activity

@activity.defn
async def scrape(url: str) -> str:
    async with httpx.AsyncClient() as c:
        r = await c.get(url)
    return r.text
```

Activity contract:

- **`@activity.defn`** decorator; sync or async signature both work.
- **Plain Python** — no sandbox, no determinism check. Any library, any I/O.
- **JSON/pydantic-serializable args + return** — same data converter rules as workflow args.
- **Idempotent or heartbeat-checkpointed** — activities can retry. If your activity isn't safe to re-run from scratch, use `activity.heartbeat(detail)` to record progress and check `activity.info().heartbeat_details` on entry.
- **Registered with the worker** — `Worker(..., activities=[scrape])`.

Pydantic AI's `TemporalAgent` auto-generates one activity per model call and per tool call, so most lessons don't write `@activity.defn` themselves. [Lesson 08](../../tracks/02-temporal/lessons/08_long_running/README.md) is the one where you do.

## What the worker needs

```python
from temporalio.client import Client
from temporalio.worker import Worker

client = await Client.connect("localhost:7233", namespace="learn-pydantic-ai")

async with Worker(
    client,
    task_queue="my-queue",          # workers and clients agree by string
    workflows=[MinimalWorkflow],
    activities=[scrape],
):
    await asyncio.Future()           # block forever
```

Required:

- **Connected client** (the worker needs the cluster reachable to poll).
- **Task queue name** — the contract between client and worker. Both sides must use the same string. (This repo standardizes on `"learn-pydantic-ai"` via `TASK_QUEUE` in [`learn_pydantic_ai/temporal.py`](../../learn_pydantic_ai/temporal.py).)
- **`workflows=[...]`** — every workflow class the worker can run.
- **`activities=[...]`** — every activity it can execute. Workflows can `execute_activity` only against registered activities.

Optional but common: `workflow_runner=` for the sandbox passthrough config (the repo's `make_workflow_runner()` handles this), `plugins=[...]` (this repo applies `PydanticAIPlugin` on the *client*, which the worker inherits — never pass it to `Worker(...)` directly).

## What the client needs

```python
handle = await client.start_workflow(
    MinimalWorkflow.run,
    "world",
    id="hello-1",                    # caller-supplied, must be unique
    task_queue="my-queue",           # must match a worker
)
result = await handle.result()
```

Required:

- **Workflow ID** — a string you choose. Reuse policy (`AllowDuplicate` / `RejectDuplicate` / `AllowDuplicateFailedOnly`) controls whether you can start a new execution with the same ID.
- **Task queue** — same string as the worker.
- **Args** — match the workflow's `run` signature, JSON-serializable.

Everything else (timeouts, retry policies, cron schedules, search attributes) is optional.

## Optional add-ons

These aren't required for a workflow to *run*; they're tools you reach for when you need them. Each links to a worked lesson.

| Need | Mechanism | Lesson |
|---|---|---|
| Mutate state from outside | `@workflow.signal` | [07](../../tracks/02-temporal/lessons/07_hitl_approval/README.md) |
| Read state from outside | `@workflow.query` | [07](../../tracks/02-temporal/lessons/07_hitl_approval/README.md) |
| Pause durably | `workflow.wait_condition(predicate)` | [02](../../tracks/02-temporal/lessons/02_stateful_workflow/README.md), [07](../../tracks/02-temporal/lessons/07_hitl_approval/README.md) |
| Wait on a clock | `await workflow.sleep(n)` (`workflow.now()` for "what time is it?") | — |
| Keep a slow activity alive | `activity.heartbeat(...)` + `heartbeat_timeout` | [08](../../tracks/02-temporal/lessons/08_long_running/README.md) |
| Customize retries / timeouts | `RetryPolicy(...)`, `start_to_close_timeout=` | [05](../../tracks/02-temporal/lessons/05_activity_config/README.md) |
| Outlive the history limit | `workflow.continue_as_new(args=[...])` | [08](../../tracks/02-temporal/lessons/08_long_running/README.md) |
| Spawn a sub-workflow | `await workflow.execute_child_workflow(...)` | — |
| Encrypt payloads end-to-end | Codec server | [codec-server.md](codec-server.md) |

## A pre-flight checklist

Before running a new workflow against a real cluster, walk this list:

- [ ] `@workflow.defn` on the class, exactly one `@workflow.run`, args are JSON-serializable.
- [ ] No top-level I/O in any module the workflow imports.
- [ ] No `random`, `time`, `datetime.now`, or network calls inside `@workflow.run` (or any method it calls). Use `workflow.*` equivalents.
- [ ] Every `execute_activity` target is registered in `Worker(activities=[...])`.
- [ ] Worker and client agree on the same `task_queue` string.
- [ ] If activities take > 60 seconds, set `start_to_close_timeout` *and* `heartbeat_timeout`, and call `activity.heartbeat()` inside the body.
- [ ] Workflow ID is meaningful and the reuse policy matches the intent.

If a workflow misbehaves, the **History tab** in the Temporal UI (<http://localhost:8080>) is the truth: every state transition is recorded as an event. Walk it top to bottom.

## References

- Temporal docs: [Workflows](https://docs.temporal.io/workflows) · [Activities](https://docs.temporal.io/activities) · [Workers](https://docs.temporal.io/workers)
- This repo's shared wiring: [`learn_pydantic_ai/temporal.py`](../../learn_pydantic_ai/temporal.py)
- Track 02 walkthrough: [`tracks/02-temporal/README.md`](../../tracks/02-temporal/README.md)
