# Lesson 07 — Human-in-the-loop with signals

> The code for this lesson is the three `.py` files in this folder. Read this
> page top to bottom; it quotes every part of the code you need to see.

## Review

In Lesson 06 you piped per-token model and tool events out of a workflow with
`event_stream_handler`, working around the sandbox forbidding `run_stream`
inside a workflow — the handler ran as an activity.

## Goal

Pause a running workflow until an external approver sends a signal. This is the
durable analogue of LangGraph's `interrupt()` — except the pause is
server-persisted, not just stored in your local checkpointer.

## Files in this lesson

| File | Role |
|---|---|
| `workflows.py` | Defines `ApprovalWorkflow`, the `@workflow.defn` class — a draft step, a `@workflow.signal` handler, and a `wait_condition` pause. The deterministic code being taught. |
| `worker.py` | The **worker process**. Registers `ApprovalWorkflow` and polls the task queue. Run it in **terminal A** and leave it running. |
| `example.py` | The **client**. Starts the workflow, waits 3 seconds, signals it, awaits the result. Run it in **terminal B**. |

Workers don't need to know about signals — the server routes a signal to
whichever worker picks up the matching workflow task. Full explanation of the
three-file layout: [Anatomy of a Temporal lesson](../../README.md#anatomy-of-a-temporal-lesson).

## How it works

Every real agent eventually needs a human review step somewhere: approve a
draft, sign off on a tool call, pick between options. With Temporal, that pause
is **first-class durable state** — the worker can crash, the laptop can sleep,
the approver can come back tomorrow, and the workflow suspends in the cluster
and resumes the instant a signal arrives.

This is [Lesson 02](../02_stateful_workflow/README.md)'s `signal` /
`wait_condition` mechanic, unchanged — but now it gates an **agent** instead of
a running tally. Lesson 02 taught the bare mechanism with no I/O so the class
machinery wasn't competing with anything else for your attention. Here the same
machinery does real work: a sync `@workflow.signal` handler mutates instance
state, and `workflow.wait_condition(predicate)` suspends the workflow body —
costing zero CPU — until that state flips. The body runs an agent first, then
parks on the predicate.

```
   ┌──────── workflow body ────────┐
   │                                │
   │  await agent.run(...)          │  ── draft (activity)
   │                                │
   │  await wait_condition(         │
   │      lambda: self._approved    │  ── DURABLE PAUSE
   │  )                              │     (no CPU, no polling)
   │                                │
   │  return ...                    │
   └────────────────────────────────┘
              ▲
              │ signal: approve(payload)
              │
        (Python client, CLI, or HTTP)
```

A `@workflow.signal` method is a sync handler that **only mutates instance
state**. The workflow body watches that state via
`workflow.wait_condition(predicate)`, which suspends the coroutine until the
predicate becomes true. Predicate re-evaluation is triggered by any state
change a signal handler makes — Temporal handles the wake-up plumbing. The
canonical shape is in [Pattern](#pattern).

## Coming from LangGraph?

| LangGraph | Temporal |
|---|---|
| `interrupt(value)` raising `GraphInterrupt` | `workflow.wait_condition(predicate)` |
| `Command(resume=...)` over the API | `handle.signal(MyWorkflow.method, payload)` |
| Thread checkpoint persisted to your store | Workflow history persisted to the Temporal cluster |

## Walk the code

### `workflows.py` — the workflow class

**`ApprovalWorkflow.__init__`** initializes `self._approved` and
`self._approval_payload`. Instance state is the bridge between signals (the
writers) and the workflow body (the reader). It runs on every workflow start
*and* every replay, so it only sets values.

```python
def __init__(self) -> None:
    self._approved: bool = False
    self._approval_payload: str | None = None
```

**The `approve` signal handler** is a `@workflow.signal` on a **sync** method.
Signal handlers must not be `async` — they mutate state and return immediately,
letting the workflow body react via `wait_condition`.

```python
@workflow.signal
def approve(self, payload: str) -> None:
    self._approval_payload = payload
    self._approved = True
```

**The `run` body** drafts with the agent, then parks on `wait_condition(...)` —
the durable pause. The lambda gets re-evaluated whenever the workflow takes a
step (typically right after a signal arrives), so the wake-up trigger is any
state mutation a signal handler makes.

```python
@workflow.run
async def run(self, topic: str) -> str:
    draft = await draft_agent.run(f"Draft a short blurb about: {topic}")
    await workflow.wait_condition(lambda: self._approved)
    return (
        f"APPROVED — feedback: {self._approval_payload}\n\n"
        f"Original draft:\n{draft.output}"
    )
```

`ApprovalWorkflow` subclasses `PydanticAIWorkflow` and declares
`__pydantic_ai_agents__ = [draft_agent]`, where `draft_agent` is a
`TemporalAgent` wrapping a plain `Agent` — note the required `name="draft_agent"`
on that agent.

### `worker.py` — the worker process

One call. Same shape as every other lesson's worker — it just registers a
workflow that happens to have a `@workflow.signal` handler. The worker never
sees the signal directly; the server routes it.

```python
await run_worker(workflows=[ApprovalWorkflow])
```

### `example.py` — the client

`start_workflow` (not `execute_workflow`) returns immediately with a **handle**;
the workflow keeps running on the worker. `execute_workflow` would block until
completion — useless here, because the workflow is going to suspend on
`wait_condition` indefinitely.

```python
handle = await client.start_workflow(
    ApprovalWorkflow.run,
    "the joys of typed Python",
    id=workflow_id,
    task_queue=TASK_QUEUE,
)
await asyncio.sleep(3)
await handle.signal(ApprovalWorkflow.approve, "looks good, ship it")
result = await handle.result()
```

`handle.signal(...)` sends the signal by name. Passing the bound method
(`ApprovalWorkflow.approve`) lets the SDK derive the signal name automatically —
the same as `.signal("approve", "...")` would. The 3-second sleep is purely for
the demo: it gives you a window to watch the workflow show up `Running` and
paused in the UI before the signal unsticks it.

## Run it

Server up first (`make temporal-up`, leave running), then two terminals:

```bash
# Terminal A — worker (Ctrl-C to stop)
make temporal-07-worker
```

```bash
# Terminal B — starter
make temporal-07
```

The starter prints the workflow ID, then auto-approves after 3 seconds. While
it's paused, click into the workflow in the UI at `http://localhost:8080` — you
will see `WorkflowTaskScheduled` events followed by a long quiet period until
the signal arrives.

## Try it

1. **Manual approval from the CLI.** Comment out the `await handle.signal(...)`
   line in `example.py`. Re-run the starter — it will print the workflow ID and
   then hang on `handle.result()`. In a third terminal, send the signal
   yourself:

   ```bash
   temporal workflow signal \
     --workflow-id <id-printed-by-starter> \
     --name approve \
     --input '"manual approval from the CLI"' \
     --namespace learn-pydantic-ai
   ```

   The starter unsticks and prints the result. (Note the JSON-encoded string —
   `'"..."'` with both quote types — the Temporal CLI expects valid JSON for
   `--input`.)

2. **Never approve.** Skip the signal. The workflow stays in `Running` forever
   (the UI will show it stuck on `WorkflowTaskScheduled`). To reclaim it:

   ```bash
   temporal workflow terminate \
     --workflow-id <id> \
     --reason "lesson cleanup" \
     --namespace learn-pydantic-ai
   ```

3. **Multiple approvers.** Add a second signal handler `reject(reason: str)`
   that flips `self._approved = True` but stores the reason and changes the
   final string. Two ways out of the same pause.

## Gotchas

- **Signal handler must be sync.** `async def approve` will deserialize fine but
  won't be picked up by the `@workflow.signal` decorator the way you expect. Use
  a sync method that mutates state; do the async work in the workflow body once
  the predicate flips.
- **State must live on `self`.** Module-level globals are not deterministic
  across replays — `__init__` runs on every workflow start (and replay), and
  that's where signal-visible state belongs.
- **`wait_condition` is not a sleep.** It costs nothing while paused (no
  polling, no CPU). It only wakes when something signals the workflow.
- **Workflows that never resume cost storage.** A workflow paused forever still
  has its history retained by the cluster. Either give the `wait_condition` a
  `timeout=` kwarg or terminate orphans explicitly.

## Bridge

You can now pause a running agent on durable, server-persisted state and resume
it on a signal from Python, the CLI, or any HTTP caller — the **pause** half of
durability, workflows that spend most of their wall-clock time waiting.
[Lesson 08](../08_long_running/README.md) handles the other half: activities
that spend most of their wall-clock time **working**. You'll meet
`start_to_close_timeout`, `heartbeat_timeout`, and the heartbeat-or-die protocol
Temporal uses to tell live workers from dead ones.

## Pattern

*The canonical shape, for the re-read.*

```python
@workflow.defn
class ApprovalWorkflow(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [my_agent]

    def __init__(self) -> None:
        self._approved: bool = False
        self._payload: str = ""

    @workflow.signal                    # MUST be sync, not async
    def approve(self, payload: str) -> None:
        self._payload = payload
        self._approved = True

    @workflow.run
    async def run(self, topic: str) -> str:
        draft = await my_agent.run(f"Draft something about: {topic}")
        await workflow.wait_condition(lambda: self._approved)
        return f"APPROVED: {self._payload}\n\n{draft.output}"
```

Send the signal from Python:
`await handle.signal(ApprovalWorkflow.approve, "ok")`. From the CLI:
`temporal workflow signal --workflow-id <id> --name approve --input '"ok"'`.
