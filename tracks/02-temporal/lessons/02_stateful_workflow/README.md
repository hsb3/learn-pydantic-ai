# Lesson 02 — A workflow is a class

> The code for this lesson is the three `.py` files in this folder. Read this
> page top to bottom; it quotes every part of the code you need to see.

## Review

In Lesson 01 you ran `GreetWorkflow` — a `@workflow.defn` **class** with one
`@workflow.run` method that called one activity. The class looked like
ceremony: one method, no state. Why not a plain function?

## Goal

Answer that question by building a workflow that genuinely *needs* to be a
class: a running tally you push numbers into from outside, read while it runs,
and that pauses until the total crosses a target. No pydantic-ai, no activity,
no I/O — just the three method types every later workflow uses:
`@workflow.run`, `@workflow.signal`, and `@workflow.query`.

## Files in this lesson

This lesson — like every lesson from here on — is a directory of three files:

| File | Role |
|---|---|
| `workflows.py` | Defines `TallyWorkflow`, the `@workflow.defn` class. This is the deterministic workflow code — the thing being taught. |
| `worker.py` | The **worker process**. Registers `TallyWorkflow` and polls the task queue for work. You run it in **terminal A** and leave it running. |
| `example.py` | The **client**. Starts the workflow, sends it signals, reads it with a query, awaits the result. You run it in **terminal B**. |

**Does Temporal require this three-file layout? No.** Temporal imposes no file
or folder structure at all — a `Worker` is built from a task-queue string and
plain lists of workflow classes and activity functions, and you could write a
whole Temporal app in one file. This track splits the three *roles* into three
*files* for two reasons: the two-terminal study loop needs a separately
runnable worker and client, and — the one real Temporal constraint — workflow
modules must be **import-safe** because the sandbox re-imports them on replay,
so the workflow class is kept alone in `workflows.py` with no import-time side
effects. Full explanation: [Anatomy of a Temporal lesson](../../README.md#anatomy-of-a-temporal-lesson).

## How it works

A Temporal workflow is a **class** because one running execution needs to share
mutable state across three different kinds of method. `GreetWorkflow` had only
`run`, so the class was invisible. `TallyWorkflow` has all three:

- **`@workflow.run`** — the body, runs once per execution.
- **`@workflow.signal`** — external *writes* into the running workflow.
- **`@workflow.query`** — external *reads* of the running workflow.

The bridge between them is **instance state**: plain attributes set in
`__init__` and mutated by signal handlers. `workflow.wait_condition` suspends
the run until that state satisfies a predicate.

```
        handle.signal(add, 5) ─┐        ┌─ handle.query(total) -> 12
        handle.signal(close) ──┤        │
                               ▼        │
                    ┌─────────────────────────────┐
                    │  TallyWorkflow instance      │
                    │    self._total   = 12        │  ◄── shared state on self
                    │    self._closed  = False     │
                    └─────────────────────────────┘
                               ▲
                    @workflow.run body:
                    await wait_condition(
                        lambda: self._total >= target  ── DURABLE PAUSE
                                or self._closed         (wakes on signal)
                    )
```

These rules govern how the methods behave:

- A **signal handler is sync** and only mutates `self`. Each call is recorded
  as an event in workflow history.
- A **query handler is sync** and only *reads* `self` — never mutates. Temporal
  may run a query during replay, so a mutating query is a determinism bug.
- The **`run` body watches `self`** via `workflow.wait_condition(predicate)`,
  which suspends the coroutine until a signal changes state enough to make the
  predicate true. Temporal does the wake-up — no polling, zero CPU while paused.
- **`__init__` runs at the start of the execution and again on every replay**,
  so it must be deterministic: just set initial values, nothing else.

Why learn this in isolation, with no agent? Because every workflow from
Lesson 03 onward is a class with exactly this anatomy. If the first time you
meet `__init__`, `@workflow.signal`, and `wait_condition` is *also* the first
time you're wrapping a pydantic-ai agent, the class machinery reads as
boilerplate you copy without understanding. Isolate it now and, when the agent
arrives, the only new thing is the agent.

## Coming from LangGraph?

| LangGraph | Temporal (this lesson) |
|---|---|
| Graph state dict (the `State` schema) | instance attributes on `self` (`self._total`) |
| `Command(update={...})` / `update_state(...)` | a `@workflow.signal` handler mutating `self` |
| `graph.get_state(thread).values` | a `@workflow.query` handler returning `self.*` |
| `interrupt()` pausing the graph | `await workflow.wait_condition(predicate)` |
| Resuming with `Command(resume=...)` | `handle.signal(Workflow.method, payload)` |

The shape is the one you know — pausable, externally readable, resumed by a
message. The differences: there's no checkpointer and no agent here (this is
the bare mechanism), and one Temporal-specific rule with no LangGraph
equivalent — state lives on `self`, never in module globals, because
`__init__`, not the module, is what re-runs on replay.

## Walk the code

### `workflows.py` — the workflow class

**`TallyWorkflow.__init__`** sets the two attributes that are the shared state
for every signal, query, and the run body. It runs on start *and* on every
replay, so it only sets values — nothing else.

```python
def __init__(self) -> None:
    self._total: int = 0
    self._closed: bool = False
```

**The `add` signal handler** — an external write. Sync, mutates state, returns.
Each `add` becomes a `WorkflowExecutionSignaled` event in history.

```python
@workflow.signal
def add(self, n: int) -> None:
    self._total += n
```

**The `close` signal handler** — a second way to satisfy the predicate: "stop
now, return what we have." Also sync.

**The `total` query handler** — an external read. Sync, returns state, never
mutates. Temporal rejects a query that writes to `self`.

```python
@workflow.query
def total(self) -> int:
    return self._total
```

**The `run` body** — one line of real logic. `wait_condition` is the durable
pause: zero CPU while waiting, re-checked only when a signal changes state.

```python
@workflow.run
async def run(self, target: int) -> int:
    await workflow.wait_condition(lambda: self._total >= target or self._closed)
    return self._total
```

### `worker.py` — the worker process

One call. `run_worker` connects to the server, installs `PydanticAIPlugin`
(dormant here — no agent yet), configures the sandboxed runner, and blocks
until Ctrl-C. `TallyWorkflow` registers no activities, so there's nothing to
pass alongside it.

```python
await run_worker(workflows=[TallyWorkflow])
```

### `example.py` — the client

`start_workflow` (not `execute_workflow`) returns a **handle** immediately —
the workflow is now running on the worker, paused inside `wait_condition`. The
handle is what lets the client signal *into* and query *out of* a workflow
that's still running.

```python
handle = await client.start_workflow(
    TallyWorkflow.run, 10, id=workflow_id, task_queue=TASK_QUEUE,
)
for n in (3, 4):
    await handle.signal(TallyWorkflow.add, n)
running = await handle.query(TallyWorkflow.total)   # 7 — still below target
await handle.signal(TallyWorkflow.add, 5)           # 7 + 5 = 12, crosses target
result = await handle.result()                      # wait_condition releases
```

## Run it

Server up first (`make temporal-up`, leave running), then two terminals:

```bash
# Terminal A — worker (Ctrl-C to stop)
make temporal-02-worker
```

```bash
# Terminal B — starter
make temporal-02
```

Expected in terminal B: the running total prints `7` after the first two `add`
signals, then the final total `12` once the third `add` crosses the target of
10 and `wait_condition` releases. Open the printed UI link and look at the
History tab — you'll see a `WorkflowExecutionSignaled` event for each `add`, a
quiet gap where the workflow was paused, and `WorkflowExecutionCompleted` at
the end.

## Try it

1. **Query mid-flight from the CLI.** Re-run the starter, and before it
   finishes, in a third terminal:
   ```bash
   temporal workflow query \
     --workflow-id <id-from-starter> \
     --type total \
     --namespace learn-pydantic-ai
   ```
   You read the live total without touching the workflow's progress.

2. **Take the `close` exit.** In `example.py`, replace the third `add(5)` with
   `await handle.signal(TallyWorkflow.close)`. The total never reaches 10, but
   `close` flips `self._closed` and the predicate's second clause releases the
   pause. The workflow returns `7`.

3. **Never satisfy the predicate.** Comment out all the signals after
   `start_workflow`. The starter hangs on `handle.result()` and the workflow
   sits in `Running` forever — zero CPU, a durable pause, not a busy loop.
   Reclaim it with `temporal workflow terminate --workflow-id <id> --namespace
   learn-pydantic-ai`.

## Gotchas

- **Signal and query handlers must be sync.** `async def add(...)` won't be
  registered the way you expect. Mutate state synchronously; do any async work
  in the `run` body once the predicate flips.
- **Queries must not mutate state.** A `@workflow.query` that writes to `self`
  is a determinism bug — Temporal may run it during replay.
- **State lives on `self`, never module globals.** `__init__` re-runs on every
  replay and reconstructs `self`; a module-level global would not be rebuilt
  deterministically, so signals could appear to "vanish" after a worker
  restart.
- **`wait_condition` is not `sleep`.** It costs nothing while paused and wakes
  only on a state change. Don't poll in a loop. For workflows that may pause
  forever, pass `timeout=` or terminate orphans explicitly.

## Bridge

You now know *why* a workflow is a class and how `signal`, `query`, and
`wait_condition` cooperate through instance state. [Lesson 03](../03_hello_durable/README.md)
keeps this exact class shape but puts a pydantic-ai `Agent` inside the `run`
body — the smallest real durable agent. The class stops being mysterious; the
only new thing is the agent. ([Lesson 07](../07_hitl_approval/README.md) is
this lesson's `wait_condition` again, gating an agent on human approval.)

## Pattern

*The canonical shape, for the re-read.*

```python
from temporalio import workflow

@workflow.defn
class TallyWorkflow:
    def __init__(self) -> None:
        self._total = 0          # shared state, rebuilt on every replay
        self._closed = False

    @workflow.signal             # external write — MUST be sync
    def add(self, n: int) -> None:
        self._total += n

    @workflow.query              # external read — MUST NOT mutate
    def total(self) -> int:
        return self._total

    @workflow.run
    async def run(self, target: int) -> int:
        await workflow.wait_condition(      # durable pause, zero CPU
            lambda: self._total >= target or self._closed
        )
        return self._total
```

Client side: `handle = await client.start_workflow(...)`, then
`await handle.signal(TallyWorkflow.add, 5)` and
`await handle.query(TallyWorkflow.total)`.
