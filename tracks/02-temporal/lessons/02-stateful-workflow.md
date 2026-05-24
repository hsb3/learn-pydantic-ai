# Lesson 02 — A workflow is a class

**Code:** `../examples/02_stateful_workflow/`

## Review

In Lesson 01 you brought up a Temporal server and ran `GreetWorkflow` — a
`@workflow.defn` **class** with a single `@workflow.run` method that called
one activity. The class looked like ceremony: why not a plain function?

## Goal

Answer that question by building a workflow that actually *needs* to be a
class: a running tally you push numbers into from outside, read while it
runs, and that pauses until the total crosses a target. No pydantic-ai, no
activity, no I/O — just the three method types every later workflow uses:
`@workflow.run`, `@workflow.signal`, and `@workflow.query`.

## TL;DR

A Temporal workflow is a class because one execution shares mutable state
across three method kinds: the `run` body, `signal` handlers (external
writes), and `query` handlers (external reads). Instance attributes set in
`__init__` are that shared state. `workflow.wait_condition(predicate)`
suspends the run — durably, at zero CPU — until a signal mutates state
enough to satisfy the predicate. Learn this state machine in isolation now;
Lesson 07's human-in-the-loop is exactly this shape with an agent bolted on.

## Why it matters

Every workflow from Lesson 03 onward is a class with this anatomy. If the
first time you meet `__init__`, `@workflow.signal`, and `wait_condition` is
*also* the first time you're wrapping a pydantic-ai agent (Lesson 03) or
gating one on human approval (Lesson 07), the class machinery reads as
boilerplate you copy without understanding. Isolating it here means that
when the agent arrives, the only new thing is the agent.

## Mental model

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

A `@workflow.signal` handler is **sync** and only mutates `self`. A
`@workflow.query` handler is **sync** and only reads `self` (never mutates).
The `run` body watches `self` via `workflow.wait_condition(predicate)`,
which suspends the coroutine until a signal changes state enough to make the
predicate true. Temporal handles the wake-up — there is no polling and no
CPU cost while paused. `__init__` runs at the start of the execution and
again on every replay, so it must be deterministic: just set initial values.

## Coming from LangGraph?

| LangGraph | Temporal (this lesson) |
|---|---|
| Graph state dict (the `State` schema) | instance attributes on `self` (`self._total`) |
| `Command(update={...})` / `update_state(...)` | a `@workflow.signal` handler mutating `self` |
| `graph.get_state(thread).values` | a `@workflow.query` handler returning `self.*` |
| `interrupt()` pausing the graph | `await workflow.wait_condition(predicate)` |
| Resuming with `Command(resume=...)` | `handle.signal(Workflow.method, payload)` |

The shape is the same one you know — pausable, externally-readable, resumed
by a message. The difference is there's no checkpointer and no agent here:
this is the bare mechanism. In Lesson 07 you'll see it wrap an agent, which
is the true `interrupt()` analogue. Note one Temporal-specific rule with no
LangGraph equivalent: state lives on `self`, never in module globals, because
`__init__` — not the module — is what re-runs on replay.

## Walk the code

1. `workflows.py:33` — `def __init__(self)` sets `self._total` and
   `self._closed`. This is the state every signal, query, and the run body
   share. Runs on start *and* on every replay → keep it deterministic.
2. `workflows.py:41` — `@workflow.signal def add(self, n)`. A **sync**
   handler that mutates state. Each call is recorded as an event in workflow
   history.
3. `workflows.py:46` — `@workflow.signal def close(self)`. A second way to
   satisfy the predicate — "stop now, return what we have."
4. `workflows.py:51` — `@workflow.query def total(self)`. A **sync** read.
   Queries must never mutate state; Temporal rejects a query that does.
5. `workflows.py:61` — `await workflow.wait_condition(lambda: ...)`. The
   durable pause. Wakes only when a signal changes the state the lambda
   reads.
6. `example.py` — `start_workflow` (not `execute_workflow`) returns a
   **handle**. The handle is what lets the client signal *into* and query
   *out of* the still-running workflow.

## Run

Server up first (`make temporal-up`, leave running), then two terminals:

```bash
# Terminal A — worker (Ctrl-C to stop)
make temporal-02-worker
```

```bash
# Terminal B — starter
make temporal-02
```

Expected in terminal B: the running total prints `7` after the first two
`add` signals, then the final total `12` once the third `add` crosses the
target of 10 and `wait_condition` releases. Open the printed UI link and look
at the History tab — you'll see `WorkflowExecutionSignaled` events for each
`add`, a quiet gap where the workflow was paused, and `WorkflowExecutionCompleted`
at the end.

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

2. **Take the `close` exit.** In `example.py`, replace the third
   `add(5)` with `await handle.signal(TallyWorkflow.close)`. Now the total
   never reaches 10, but `close` flips `self._closed` and the predicate's
   second clause releases the pause. The workflow returns `7`.

3. **Never satisfy the predicate.** Comment out all the signals after
   `start_workflow`. The starter hangs on `handle.result()` and the workflow
   sits in `Running` forever (zero CPU — it's a durable pause, not a busy
   loop). Reclaim it with `temporal workflow terminate --workflow-id <id>
   --namespace learn-pydantic-ai`.

## Gotchas

- **Signal and query handlers must be sync.** `async def add(...)` won't be
  registered the way you expect. Mutate state synchronously; do any async
  work in the `run` body once the predicate flips.
- **Queries must not mutate state.** A `@workflow.query` that writes to
  `self` is a determinism bug — Temporal may run it during replay. Reads only.
- **State lives on `self`, never module globals.** `__init__` re-runs on
  every replay and reconstructs `self`; a module-level global would not be
  rebuilt deterministically, so signals could appear to "vanish" after a
  worker restart.
- **`wait_condition` is not `sleep`.** It costs nothing while paused and
  wakes only on a state change. Don't poll in a loop. For workflows that may
  pause forever, pass `timeout=` or terminate orphans explicitly.

## Bridge

You now know *why* a workflow is a class and how `signal`, `query`, and
`wait_condition` cooperate through instance state. Lesson 03 keeps this exact
class shape but puts a pydantic-ai `Agent` inside the `run` body — the
smallest real durable agent. The class stops being mysterious; the only new
thing is the agent.

## Pattern

*The canonical shape, for the re-read.*

```python
from temporalio import workflow

@workflow.defn
class TallyWorkflow:
    def __init__(self) -> None:
        self._total = 0            # shared state, rebuilt on every replay
        self._closed = False

    @workflow.signal               # external write — MUST be sync
    def add(self, n: int) -> None:
        self._total += n

    @workflow.query                # external read — MUST NOT mutate
    def total(self) -> int:
        return self._total

    @workflow.run
    async def run(self, target: int) -> int:
        await workflow.wait_condition(           # durable pause, zero CPU
            lambda: self._total >= target or self._closed
        )
        return self._total
```

Client side: `handle = await client.start_workflow(...)`, then
`await handle.signal(TallyWorkflow.add, 5)` and
`await handle.query(TallyWorkflow.total)`.
