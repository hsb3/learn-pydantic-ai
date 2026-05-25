# Lesson 03 — Hello durable agent

> The code for this lesson is the three `.py` files in this folder. Read this
> page top to bottom; it quotes every part of the code you need to see.

## Review

In Lesson 02 you built `TallyWorkflow`: a plain `@workflow.defn` class with
state on `self`, `@workflow.signal` / `@workflow.query` methods, and a
`wait_condition` pause. Hold that class shape in mind — this lesson reuses it
exactly and adds one thing: an agent.

## Goal

Wrap a Pydantic AI `Agent` in a `TemporalAgent`, run it inside a
`@workflow.defn` class, and execute that workflow from a separate client
process. This is the smallest "real" durable agent — everything later in the
track is a refinement of these three files.

## Files in this lesson

| File | Role |
|---|---|
| `workflows.py` | Defines the `Agent`, the `TemporalAgent` wrapper, and `HelloWorkflow` — the `@workflow.defn` class. The deterministic code being taught. |
| `worker.py` | The **worker process**. Registers `HelloWorkflow` and polls the task queue for work. Run it in **terminal A** and leave it running. |
| `example.py` | The **client**. Starts one workflow execution, waits for the result, prints it. Run it in **terminal B**. |

**Does Temporal require this three-file layout? No** — a `Worker` is just a
task-queue string plus lists of workflow classes and activity functions, and a
whole Temporal app can live in one file. This track splits the three roles into
three files for the two-terminal study loop and to keep `workflows.py`
import-safe. Full explanation: [Anatomy of a Temporal lesson](../../README.md#anatomy-of-a-temporal-lesson).

## How it works

Three pieces turn a Track 01 agent into a durable one: build a normal `Agent`
(now with a required `name=`), wrap it in a `TemporalAgent` so its model and
tool calls become Temporal activities, and reference it from a
`PydanticAIWorkflow` subclass — which is the Lesson 02 workflow class with
agent-activity auto-registration mixed in. Inside `run`, `await agent.run(prompt)`
reads exactly like Track 01; the durability is invisible. The canonical shape
is in [Pattern](#pattern).

This matters because Track 01 agents lived in one Python process: a crash means
restarting from scratch. A Temporal-backed agent crashes with the worker, and
the next worker picks up where the last one died — model output and tool
returns are memoized in workflow history. You get retries, durability, and an
inspectable audit log without rewriting any agent code.

You already have the workflow class from Lesson 02. Here is each piece on its
own, before the composed picture.

### 1. `Agent` — unchanged from Track 01

```python
_base = Agent(model=FLASH, name="hello_durable", instructions="…")
```

The same `Agent` you know. The one new requirement is a `name=`: Temporal
derives deterministic activity names from it (`hello_durable__model_request`),
so it becomes mandatory the moment you wrap the agent.

### 2. `TemporalAgent` — wrap it to make its calls durable

```python
hello_agent = TemporalAgent(_base)
```

`TemporalAgent` re-points the agent's model requests and tool calls at Temporal
activities. In Lesson 01 you scheduled an activity *by hand* with
`workflow.execute_activity(say_hello, ...)`; `TemporalAgent` does exactly that
for you, for every model and tool call — you never write `execute_activity` for
them. Outside a workflow the wrapper is transparent: `_base.run_sync(...)` still
works normally.

### 3. `PydanticAIWorkflow` — the Lesson 02 class, plus agent registration

```python
@workflow.defn
class HelloWorkflow(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [hello_agent]
```

This is the exact `@workflow.defn` class from Lesson 02 — a `run` method, and
(later) `signal` / `query` methods — with one base class added.
`PydanticAIWorkflow` is how the worker finds your agents: at startup
`PydanticAIPlugin` walks the `__pydantic_ai_agents__` list and registers each
agent's auto-generated model + tool activities. The plain `@workflow.defn`
classes in Lessons 01–02 didn't need it because they had no agent activities to
register.

### Composed

```
   pydantic_ai.Agent          --> the same agent from Track 01
       wrapped by
   TemporalAgent               --> reroutes model + tool calls to activities
       referenced from
   PydanticAIWorkflow subclass --> the Lesson 02 class + agent registration
```

The `await hello_agent.run(prompt)` line inside `run` looks identical to Track
01. The difference is *where* the work happens: model requests are scheduled as
activities on the task queue, and their results land in workflow history before
the next line of workflow code runs.

## Coming from LangGraph?

This is the authoritative translation table for the whole track. Bookmark it.

| Temporal | LangGraph / langgraph-api analogue |
|---|---|
| `@workflow.defn` class + `PydanticAIWorkflow` | a graph compiled with a persistent checkpointer |
| `TemporalAgent.run()` inside a workflow | `graph.invoke()` with checkpointer-backed guarantees |
| `@activity.defn` (or any auto-lifted activity) | a node whose result is memoized to durable storage |
| `Worker` + `task_queue` | the `langgraph-api` server + its worker pool |
| `client.start_workflow(...)` | `langgraph-sdk` `Client.runs.create(...)` |
| Workflow ID | `thread_id` |
| `workflow.wait_condition(...)` | `interrupt()` |
| Signal sent to a running workflow | `Command(resume=...)` posted to the API |
| Query on a running workflow | reading `state.values` for a thread |
| Determinism rule (no `random`, `datetime.now`, `httpx.get`) | "side-effecting code goes in tools / IO-wrapped nodes" |
| `continue-as-new` | resetting a thread's checkpoint to start fresh |
| `workflow.now()` / `workflow.sleep()` | the same — clock + sleep go through the checkpointer / runtime |

You'll feel at home with `client.start_workflow + handle.result()`. The big new
constraint is **strict determinism inside workflow code**. LangGraph and
Temporal both want side-effecting work pushed out of orchestration code; the
difference is enforcement: LangGraph treats it as a convention (you can
technically call `httpx.get()` in a node and the checkpointer will persist the
result, but you'll lose replayability if you do), while Temporal's sandbox
actively blocks restricted operations inside `@workflow.run` so the mistake
fails fast. `PydanticAIPlugin` does the lift for you for model + tool calls —
that's why `await my_agent.run(...)` is workflow-safe.

## Walk the code

### `workflows.py` — the agent and the workflow class

This file defines the three objects from [How it works](#how-it-works) in
order — `_base` (the plain `Agent`), `hello_agent` (the `TemporalAgent`
wrapper), and `HelloWorkflow` (the `PydanticAIWorkflow` subclass). Two details
the conceptual sketch above left out:

**The real `_base` instructions** are a concrete string, not the `…`
placeholder — and `name=` is mandatory, because `TemporalAgent` derives
deterministic activity names from it:

```python
_base = Agent(
    model=FLASH,
    name="hello_durable",
    instructions="Reply in one short sentence.",
)
```

**`HelloWorkflow.run`** — the body, which How it works didn't show — is one
prompt in, one string out. The `await hello_agent.run(prompt)` line reads like
Track 01, but the model request is scheduled as an activity and memoized in
workflow history before `run` continues:

```python
@workflow.run
async def run(self, prompt: str) -> str:
    result = await hello_agent.run(prompt)
    return result.output
```

### `worker.py` — the worker process

**`main`** makes one call. `run_worker` connects to the server, installs
`PydanticAIPlugin`, configures the sandboxed workflow runner with the package as
a passthrough, and blocks on SIGINT/SIGTERM. All this worker has to do is hand
it the workflow list.

```python
async def main() -> None:
    await run_worker(workflows=[HelloWorkflow])
```

### `example.py` — the client

**`main`** connects to the same Temporal server the worker is polling, then
calls `client.execute_workflow` — which is "start + wait." (For
fire-and-forget, use `start_workflow` and call `.result()` on the returned
handle later, as Lesson 02 did.) Note the per-run UUID in `workflow_id`.

```python
workflow_id = f"lesson-03-{uuid.uuid4().hex[:8]}"
result = await client.execute_workflow(
    HelloWorkflow.run,
    "Where does 'hello world' come from?",
    id=workflow_id,
    task_queue=TASK_QUEUE,
)
print("Result:", result)
```

## Run it

Two terminals. Server first (`make temporal-up`, leave running):

```bash
# Terminal A — worker (Ctrl-C to stop)
make temporal-03-worker
```

```bash
# Terminal B — starter (re-run as often as you like)
make temporal-03
```

Expected output in terminal B: `Result: <one sentence about "hello world">`
plus a Temporal UI URL. Open it and click into the workflow.

## Try it

1. **Change the prompt** in `example.py` to something multi-step ("Plan a
   3-stop trip to Kyoto."). Re-run only the starter; the worker stays up. Same
   `workflow_id`-prefix, new UUID — Temporal shows them as separate executions.
2. **Kill the worker mid-run.** Start a workflow, then `Ctrl-C` the worker
   before the model responds. The model activity stays scheduled. Restart the
   worker; the activity is picked up and the workflow completes.
3. **Inspect history.** In the UI, click the workflow's "History" tab. Count
   the `ActivityTaskScheduled` events — for a no-tool agent it's exactly one
   model-request activity.

## Gotchas

- **`name=` on the Agent is mandatory.** Without it, `TemporalAgent(...)` raises
  at import time.
- **No `print()` inside `@workflow.run`.** Use `workflow.logger.info(...)` —
  `print` goes through `sys.stdout`, which the sandbox treats as
  non-deterministic.
- **Absolute imports inside the lesson dir.** `from workflows import
  HelloWorkflow`, not `from .workflows import ...`. The Makefile runs each
  lesson script with the lesson dir as `sys.path[0]`.
- **Don't forget `workflow_runner=make_workflow_runner()`.** It marks
  `learn_pydantic_ai` as a sandbox passthrough — otherwise the sandbox tries to
  re-import the package and `Path(__file__).resolve()` blows up.
- **Workflow ID conflicts.** Reusing a completed workflow's exact ID raises
  `WorkflowAlreadyStartedError` by default. The starter appends a UUID for this
  reason.

## Bridge

You can now wrap a pydantic-ai agent in a durable workflow and run it from a
separate client. The workflow above had zero tools, so its history is boring.
[Lesson 04](../04_workflow_vs_activity/README.md) adds one `@agent.tool` and
you'll see two more activities show up in the timeline — the
workflow-vs-activity boundary made visible.

## Pattern

*The canonical shape, for the re-read.*

```python
from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import PydanticAIWorkflow, TemporalAgent
from temporalio import workflow

_base = Agent(model=FLASH, name="hello_durable", instructions="…")
hello_agent = TemporalAgent(_base)           # name= on the Agent is REQUIRED

@workflow.defn
class HelloWorkflow(PydanticAIWorkflow):      # Lesson 02 class + agent registration
    __pydantic_ai_agents__ = [hello_agent]    # plugin auto-registers activities

    @workflow.run
    async def run(self, prompt: str) -> str:
        return (await hello_agent.run(prompt)).output
```

Run: `make temporal-03-worker` (A) + `make temporal-03` (B).
