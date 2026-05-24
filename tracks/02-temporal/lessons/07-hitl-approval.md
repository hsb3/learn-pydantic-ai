# Lesson 07 — Human-in-the-loop with signals

**Code:** `../examples/07_hitl_approval/`

## Review

- In Lesson 06 you piped per-token model and tool events out of a workflow with `event_stream_handler`.
- That worked around the sandbox forbidding `run_stream` inside a workflow — the handler ran as an activity.

## Goal

Pause a running workflow until an external approver sends a signal. This
is the durable analogue of LangGraph's `interrupt()` — except the pause
is server-persisted, not just stored in your local checkpointer.

## TL;DR

Here you pause a running workflow until an external approver sends a signal — the durable analogue of LangGraph's `interrupt()`, except the pause is server-persisted rather than held in a local checkpointer. The key mechanic: a sync `@workflow.signal` handler mutates instance state, and `workflow.wait_condition(predicate)` suspends the workflow body (costing zero CPU) until that state flips. The canonical shape is in [Pattern](#pattern).

## Why it matters

Every real agent eventually needs a human review step somewhere: approve
a draft, sign off on a tool call, pick between options. With Temporal,
that pause is **first-class durable state**: the worker can crash, the
laptop can sleep, the approver can come back tomorrow — the workflow
suspends in the cluster and resumes the instant a signal arrives.

## Mental model

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

A `@workflow.signal` method is a sync handler that **only mutates
instance state**. The body of the workflow watches that state via
`workflow.wait_condition(predicate)`, which suspends the coroutine until
the predicate becomes true. Predicate re-evaluation is triggered by any
state change a signal handler makes — Temporal handles the wake-up
plumbing.

| LangGraph | Temporal |
|---|---|
| `interrupt(value)` raising `GraphInterrupt` | `workflow.wait_condition(predicate)` |
| `Command(resume=...)` over the API | `handle.signal(MyWorkflow.method, payload)` |
| Thread checkpoint persisted to your store | Workflow history persisted to the Temporal cluster |

## Walk the code

- `examples/07_hitl_approval/workflows.py:50` — `__init__` initializes
  `self._approved` and `self._approval_payload`. Instance state is the
  bridge between signals (writers) and the workflow body (reader).
- `examples/07_hitl_approval/workflows.py:55` — `@workflow.signal` on a
  **sync** method named `approve`. Signal handlers must not be async —
  they mutate state and return immediately.
- `examples/07_hitl_approval/workflows.py:64` — `wait_condition(...)` is
  the durable pause. The lambda gets re-evaluated whenever the workflow
  takes a step (typically right after a signal arrives).
- `examples/07_hitl_approval/example.py:34` — `start_workflow` (not
  `execute_workflow`) so we hold a handle and don't block waiting for the
  result. `handle.signal(ApprovalWorkflow.approve, payload)` sends the
  signal by method reference; Temporal derives the name.

## Run (two-terminal pattern)

```bash
# terminal A
make temporal-up               # if not already
make temporal-07-worker

# terminal B
make temporal-07
```

The starter prints the workflow ID, then auto-approves after 3 seconds.
While it's paused, click into the workflow in the UI at
`http://localhost:8080` — you will see `WorkflowTaskScheduled` events
followed by a long quiet period until the signal arrives.

## Try it

1. **Manual approval from the CLI.** Comment out the `await handle.signal(...)`
   line in `example.py`. Re-run the starter — it will print the workflow
   ID and then hang on `handle.result()`. In a third terminal, send the
   signal yourself:

   ```bash
   temporal workflow signal \
     --workflow-id <id-printed-by-starter> \
     --name approve \
     --input '"manual approval from the CLI"' \
     --namespace learn-pydantic-ai
   ```

   The starter unsticks and prints the result. (Note the JSON-encoded
   string — `'"..."'` with both quote types — the Temporal CLI expects
   valid JSON for `--input`.)

2. **Never approve.** Skip the signal. The workflow stays in `Running`
   forever (the UI will show it stuck on `WorkflowTaskScheduled`). To
   reclaim it:

   ```bash
   temporal workflow terminate \
     --workflow-id <id> \
     --reason "lesson cleanup" \
     --namespace learn-pydantic-ai
   ```

3. **Multiple approvers.** Add a second signal handler `reject(reason: str)`
   that flips `self._approved = True` but stores the reason and changes
   the final string. Two ways out of the same pause.

## Gotchas

- **Signal handler must be sync.** `async def approve` will deserialize
  fine but won't be picked up by the `@workflow.signal` decorator the way
  you expect. Use a sync method that mutates state; do the async work in
  the workflow body once the predicate flips.
- **State must live on `self`.** Module-level globals are not deterministic
  across replays — `__init__` runs on every workflow start (and replay)
  and that's where signal-visible state belongs.
- **`wait_condition` is not a sleep.** It costs nothing while paused (no
  polling, no CPU). It only wakes when something signals the workflow.
- **Workflows that never resume cost storage.** A workflow paused forever
  still has its history retained by the cluster. Either give the
  `wait_condition` a `timeout=` kwarg or terminate orphans explicitly.

## Bridge

Lesson 07 handled the **pause** half of durability — workflows that
spend most of their wall-clock time waiting. Lesson 08 handles the other
half: activities that spend most of their wall-clock time **working**.
You'll meet `start_to_close_timeout`, `heartbeat_timeout`, and the
heartbeat-or-die protocol Temporal uses to tell live workers from dead ones.

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

Send the signal from Python: `await handle.signal(ApprovalWorkflow.approve, "ok")`. From the CLI: `temporal workflow signal --workflow-id <id> --name approve --input '"ok"'`.
