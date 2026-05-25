# Lesson 01 — Temporal in 15 minutes

> The code for this lesson is `01_temporal_tour.ipynb` in this folder. Read
> this page top to bottom; it quotes every part of the code you need to see.

## Goal

Meet the four primitives every later lesson is built on — **workflow**,
**activity**, **worker**, **task queue** — by running one workflow end to end.
This lesson is a self-contained notebook: it starts a throwaway Temporal server
in-process, so there is nothing to install or boot up first. No pydantic-ai
yet — just Temporal.

## Files in this lesson

This lesson is a single self-contained notebook:

| File | Role |
|---|---|
| `01_temporal_tour.ipynb` | The end-to-end tour. Defines an activity and a workflow, boots an in-process server, runs the workflow, and inspects the result — all in one file. |

**Why a single notebook, when every other lesson is a three-file directory?**
Lesson 01 bootstraps its own Temporal server in-process via
`WorkflowEnvironment.start_local()`. That one call replaces two pieces of
infrastructure: it needs no `make temporal-up` docker stack, and it runs the
worker inside the same `async with` block as the client, so there is no
separate worker terminal. With the server and worker collapsed into the
notebook, you can poke all four primitives in one file and watch the whole
loop execute top to bottom.

From Lesson 02 onward the format switches to the standard directory +
two-terminal pattern: `workflows.py` / `worker.py` / `example.py`, a docker
server you bring up once, and a worker you run in its own terminal. That shift
is announced here so it doesn't surprise you. The reasoning behind the
three-file layout — and the one real Temporal constraint that motivates it — is
in [Anatomy of a Temporal lesson](../../README.md#anatomy-of-a-temporal-lesson).

## How it works

Temporal runs your code *durably*. A **workflow** is the orchestration —
deterministic code with no clocks, randomness, or network. An **activity** is
where every side effect goes: HTTP, file I/O, model calls. A **worker** polls a
**task queue** and runs both, and the server records every step so a crash
replays from history instead of starting over.

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
(`@activity.defn`) for anything with side effects: HTTP calls, file I/O,
database queries, model inference. The activity's return value is stored in
workflow history so that on replay the same code path is reconstructed
deterministically.

> **Why a class and not a function?** For `GreetWorkflow` it looks like
> ceremony — one method, no state. The class earns itself in Lesson 02, where
> a workflow holds state and exposes `@workflow.signal` / `@workflow.query`
> methods alongside `run`, all sharing instance attributes. For now, read it
> as "a class with one `run` method."

Why this matters: durable agents are durable *because* the underlying Temporal
primitives guarantee it. If you've never run a workflow before, the pydantic-ai
wrapping in Lesson 03 will feel like magic. After this lesson it will feel like
a thin layer of glue on top of mechanics you understand. The canonical shape is
in [Pattern](#pattern) at the bottom.

## Coming from LangGraph?

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

### `01_temporal_tour.ipynb`

The notebook runs top to bottom in five numbered sections (after an imports
cell at the top):

1. **Define an activity** — the `say_hello` activity.
2. **Define a workflow** — the `GreetWorkflow` class.
3. **Start an ephemeral server + worker** — `WorkflowEnvironment.start_local()`
   boots a real Temporal server in a subprocess, a `Worker` registers the
   workflow and activity, and `execute_workflow` runs it.
4. **What just happened** — a step-by-step trace of the history events that run
   produced.
5. **(Optional) connect to your docker stack** — a cell that reconnects via
   `connect()` so the run shows up in the Temporal UI. Skip on first read; run
   it after you've brought up the docker server below.

**The `say_hello` activity** — a side-effecting function. The `@activity.defn`
decorator marks it as something a workflow may invoke through Temporal instead
of calling directly. Here it just returns a string; in a real lesson it would
hit an API or run model inference.

```python
@activity.defn
async def say_hello(name: str) -> str:
    """Side-effecting function. Could call an API; here it just returns a string."""
    return f"Hello, {name}!"
```

**The `GreetWorkflow` class** — the simplest possible workflow. It is a class
decorated with `@workflow.defn` and holds one `@workflow.run` method. Workflow
code is deterministic — no `random`, no `datetime.now()`, no `httpx.get()`.
Anything non-deterministic goes in an activity, invoked via
`workflow.execute_activity(...)`; the activity's result is memoized in workflow
history so replay reproduces the same state.

```python
@workflow.defn
class GreetWorkflow:
    """The simplest possible Temporal workflow — one activity call."""

    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            say_hello,
            name,
            start_to_close_timeout=timedelta(seconds=10),
        )
```

**The server + worker** — `WorkflowEnvironment.start_local()` spins up a real
Temporal server in a subprocess and tears it down when the `async with` exits.
The `Worker` registers `GreetWorkflow` and `say_hello` against the
`lesson-01-tour` task queue, and `execute_workflow` starts the workflow and
awaits its result. `UnsandboxedWorkflowRunner` is used here only because
Jupyter's `__main__` module lacks the `__file__` attribute the default sandbox
needs — every other lesson runs as a real `.py` worker with the sandbox on.

## Run it

The notebook is self-contained — it boots its own Temporal server in-process,
so you can run it with nothing else set up:

- Open `01_temporal_tour.ipynb` in VS Code and run the cells top to bottom.

You'll see `Hello, Henry!` printed — a workflow that started, called an
activity, and returned, all on a throwaway server that is gone the moment the
cell finishes. Nothing appears at `http://localhost:8080`: that run never
touched the docker server.

### One-time setup for the rest of the track

Every lesson from 02 on uses a **persistent** Temporal server you run via
docker — not the in-process one. Set it up now so it's ready:

```bash
make temporal-up        # postgres + Temporal server + web UI on :8080
make temporal-status    # should say SERVING
```

Then, if you want to watch a run land in the Temporal UI, run the notebook's
optional last section: it reconnects to this docker server via `connect()`, and
the workflow shows up at `http://localhost:8080` under namespace
`learn-pydantic-ai`.

## Try it

1. **Break the activity.** Edit `say_hello` to `raise RuntimeError("boom")` and
   re-run the notebook. The activity fails and Temporal retries it per the
   default `RetryPolicy` (exponential backoff, capped attempts) before the
   workflow gives up — the retry attempts show up in the cell output.

2. **CLI tour (needs the docker server).** After `make temporal-up`, run the
   notebook's optional last section — that puts a workflow on the docker
   server. Then, in a terminal:
   ```bash
   temporal workflow list --namespace learn-pydantic-ai
   temporal workflow describe --workflow-id <id> --namespace learn-pydantic-ai
   temporal workflow show --workflow-id <id> --namespace learn-pydantic-ai
   ```
   These query the docker server — the in-process run from the main notebook
   path is invisible to them.

3. **Note what the notebook does NOT enforce.** This notebook runs the workflow
   with `UnsandboxedWorkflowRunner` (Jupyter's `__main__` has no `__file__` for
   the default sandbox to inspect), so a non-deterministic call like
   `datetime.now()` in the workflow body runs without complaint here. Every
   *other* lesson runs as a real `.py` worker with the sandbox on — and there
   that same line is blocked. You'll trigger the block deliberately in
   [Lesson 04](../04_workflow_vs_activity/README.md)'s "Try it." The takeaway:
   determinism is a hard constraint in production, not just a convention.

## Gotchas

These all concern the `make temporal-up` docker setup above — the in-process
notebook path itself has none of these failure modes.

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

You've run one workflow that calls one activity end to end, and you have a
working mental model of the four primitives.
[Lesson 02](../02_stateful_workflow/README.md) builds a workflow that
genuinely *needs* to be a class — one that holds state and takes signals and
queries, still with no pydantic-ai in sight. That's where the class structure
stops looking like ceremony. Lesson 03 then puts a real pydantic-ai `Agent`
inside that same class shape.

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
