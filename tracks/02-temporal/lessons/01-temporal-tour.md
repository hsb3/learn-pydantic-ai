# Lesson 01 — Temporal in 15 minutes

**Code:** `../examples/01_temporal_tour.py` (paired notebook)

## TL;DR

Temporal runs your code *durably*. A **workflow** is the orchestration —
deterministic code with no clocks, randomness, or network. An **activity** is
where every side effect goes: HTTP, file I/O, model calls. A **worker** polls a
**task queue** and runs both, and the server records every step so a crash
replays from history instead of starting over. This lesson brings up your own
server and runs one workflow that calls one activity — no pydantic-ai yet. The
canonical shape is in [Pattern](#pattern) at the bottom.

## Goal

Bring up your own Temporal server and meet the four primitives every later
lesson is built on: **workflow**, **activity**, **worker**, **task queue**.
No pydantic-ai yet — just Temporal.

## Why it matters

Durable agents are durable *because* the underlying Temporal primitives
guarantee it. If you've never run a workflow before, the pydantic-ai
wrapping in Lesson 03 will feel like magic. After this lesson it will feel
like a thin layer of glue on top of mechanics you understand.

## Mental model

```
                                ┌──────────────────┐
   client ──start workflow──►   │   Temporal       │
                                │   server         │
   worker ──poll task queue──►  │   (durable)      │
                                └──────────────────┘
```

The **server** is the source of truth. It records every event. The **client**
asks "please run workflow X with input Y." The **worker** polls the task
queue, finds work to do, executes it, and reports the result back. If the
worker crashes mid-task, the server re-issues the task to another worker.

A **workflow** is a Python **class** (`@workflow.defn`) with a `@workflow.run`
method that runs inside that machinery. It calls **activities**
(`@activity.defn`) for anything with side-effects: HTTP calls, file I/O,
database queries, model inference. The activity's return value is stored in
workflow history so that on replay the same code path is reconstructed
deterministically.

> **Why a class and not a function?** For `GreetWorkflow` it looks like
> ceremony — one method, no state. The class earns itself in Lesson 02, where
> a workflow holds state and exposes `@workflow.signal` / `@workflow.query`
> methods alongside `run`, all sharing instance attributes. For now, read it
> as "a class with one `run` method."

## Coming from LangGraph / langgraph-api?

| Temporal | LangGraph analogue |
|---|---|
| Workflow | a graph compiled with a persistent checkpointer |
| Activity | a node whose result is memoized to durable storage |
| Worker + task queue | `langgraph-api` server + worker pool |
| Workflow `Client` | `langgraph-sdk` `Client` |
| Workflow ID | thread ID |
| Signal | `Command(resume=...)` arriving over the network |
| Query | reading `state.values` for a thread |
| Determinism (no `random`, `time.time`, `httpx.get` in workflow code) | "side-effecting code goes in tools/nodes wrapped with checkpoint-safe IO" |
| `continue-as-new` | resetting checkpoint to start fresh |

You'll feel at home immediately with start_workflow + get a handle + poll
or signal it. The big new constraint is **determinism inside workflow code**:
LangGraph lets you call `httpx.get()` directly in a node (the checkpointer
just persists the result); Temporal forbids it in workflows and forces you
to put it in an activity.

## Walk the code

The notebook at `../examples/01_temporal_tour.py` is an end-to-end tour:

1. **Cell 1** — connect to your local server via `learn_pydantic_ai.connect()`.
2. **Cell 2** — define a trivial `Greet` workflow + `say_hello` activity.
3. **Cell 3** — start a worker in the background (using `WorkflowEnvironment`
   to stay self-contained inside the notebook — no separate terminal needed
   for this lesson only).
4. **Cell 4** — start the workflow, await the result, print it.
5. **Cell 5** — open the Temporal UI and click into the workflow's history.

## Run

First, your server (run once, leave running):

```bash
make temporal-up
make temporal-status   # should say SERVING
```

Then either:

- Open `../examples/01_temporal_tour.ipynb` in VS Code, or
- Sync + execute headless: `make nb-sync && make nb-exec`

Visit `http://localhost:8080` and find the workflow you just ran under
namespace `learn-pydantic-ai`.

## Try it

1. **CLI tour.** With the worker still running, open a third terminal and
   try:
   ```bash
   temporal workflow list --namespace learn-pydantic-ai
   temporal workflow describe --workflow-id <id> --namespace learn-pydantic-ai
   temporal workflow show --workflow-id <id> --namespace learn-pydantic-ai
   ```
2. **Break the activity.** Edit `say_hello` to `raise RuntimeError("boom")`.
   Re-run the workflow. In the UI, watch Temporal retry the activity per the
   default `RetryPolicy` (exponential backoff, capped attempts).
3. **Note what the notebook does NOT enforce.** This notebook runs the
   workflow with `UnsandboxedWorkflowRunner` (Jupyter's `__main__` has no
   `__file__` for the default sandbox to inspect), so a non-deterministic
   call like `datetime.now()` in the workflow body runs without complaint
   here. Every *other* lesson runs as a real `.py` worker with the sandbox
   on — and there that same line is blocked. You'll trigger the block
   deliberately in Lesson 04's "Try it." The takeaway: determinism is a hard
   constraint in production, not just a convention.

## Gotchas

- **`docker compose` not `docker-compose`.** The Makefile uses the v2 plugin
  syntax. If you have only the old python `docker-compose` binary, install
  Docker Desktop or `brew install docker-compose-v2`.
- **Port 7233 already in use.** Another Temporal install? Run
  `make temporal-down` first, or change the port in the compose file.
- **`temporal operator cluster health` returns "connection refused"** for ~20s
  after `make temporal-up`. The auto-setup image needs to migrate the
  Postgres schema on first boot. Wait, retry.
- **Namespace not found.** Auto-setup creates `learn-pydantic-ai` on first
  boot via `DEFAULT_NAMESPACE`. If you nuked the volume (`temporal-clean`),
  the next `temporal-up` recreates it.

## Bridge

Now that you have a server and a working mental model, Lesson 02 builds a
workflow that genuinely *needs* to be a class — one that holds state and
takes signals and queries, still with no pydantic-ai in sight. That's where
the class structure stops looking like ceremony. Lesson 03 then puts a real
pydantic-ai `Agent` inside that same class shape.

## Pattern

*The canonical shape, for the re-read.*

```bash
make temporal-up        # postgres + server + UI on :8080
make temporal-status    # cluster health (should say SERVING)
```

```python
from datetime import timedelta
from temporalio import activity, workflow

@activity.defn
async def say_hello(name: str) -> str:        # side effects live here
    return f"Hello, {name}!"

@workflow.defn
class GreetWorkflow:                            # a class with one run method
    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            say_hello, name, start_to_close_timeout=timedelta(seconds=10),
        )
```

Workflow = deterministic orchestration. Activity = side-effecting work.
Worker polls a task queue and runs both.
