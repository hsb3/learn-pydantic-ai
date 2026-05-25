# Lesson 10 — Capstone: headless research workflow

> The code for this lesson is the `.py` files in this folder, including the
> `agents/` sub-package. Read this page top to bottom; it quotes every part of
> the code you need to see.

## Review

In Lesson 09 you wired `LogfirePlugin` so every workflow execution became a
trace tree of model, tool, and HTTP spans — correlated with the Temporal
history you see in the UI.

## Goal

Compose **three TemporalAgents** — a clarifier, a researcher, and a writer —
inside a single durable workflow that pauses for human approval before
returning. This is the multi-agent + HITL pattern you've been building toward
since Lesson 03. Everything in the track converges here.

## Files in this lesson

| File | Role |
|---|---|
| `workflow.py` | Defines `ResearchWorkflow`, the `@workflow.defn` class. Registers all three agents via `__pydantic_ai_agents__` and orchestrates clarifier → researcher → writer with a final approval gate. |
| `worker.py` | The **worker process**. Registers `ResearchWorkflow`; the plugin registers the three agents' activities. Run in **terminal A**, leave running. |
| `starter.py` | The **client**. Starts the workflow, sleeps 5s, signals `approve`, awaits the result. Run in **terminal B**. |
| `schemas.py` | Plain `BaseModel`s for the inter-agent handoffs (`ClarifiedQuestion`, `ResearchFindings`, `ApprovalPayload`). No Temporal-specific shape. |
| `agents/clarifier.py` | The clarifier `TemporalAgent` — narrows a vague topic into one researchable question. No tools. |
| `agents/researcher.py` | The researcher `TemporalAgent` — answers the question via two `@_base.tool_plain` lookup tools. |
| `agents/writer.py` | The writer `TemporalAgent` — turns the findings into a short report. No tools. |

**New this lesson:** the layout shifts from lessons 02–09. The workflow file is
`workflow.py` (**singular** — this lesson defines one workflow class, where the
plural `workflows.py` earlier hinted at a file that could hold several). The
client is `starter.py`, not `example.py`. And the three agents move into an
`agents/` **sub-package** — one module per agent, each exposing a single
module-level `TemporalAgent`, with `agents/__init__.py` re-exporting all three.
This keeps each agent's prompt and tools self-contained as the count grows. The
three *roles* — workflow definition, worker, client — are unchanged; only the
names and the agent packaging differ. Full explanation of the role split:
[Anatomy of a Temporal lesson](../../README.md#anatomy-of-a-temporal-lesson).

## How it works

Real production agents almost never run as a single model call. They fan out
into specialists — each with focused prompts and small tool surfaces — and route
through review steps before any irreversible action. Doing that on raw asyncio
gives you no resilience: a crash mid-pipeline loses the work in flight.

This lesson composes three agents — clarifier → researcher → writer — as
sequential `await agent.run(...)` calls inside one `PydanticAIWorkflow`, then
gates the return on a HITL approval. Two mechanics carry it: `__pydantic_ai_agents__
= [...]` registers all three agents (each agent's `name=` becoming its
activity-name prefix), and a final `workflow.wait_condition` holds the durable
pause.

```
   topic ───► clarifier ───► researcher ───► writer ───► [HITL] ───► report
              (model)     (model + tools)    (model)     (signal)
              activity      activities       activity     pause
```

Each `await agent.run(...)` line is one or more activity-scheduling events in
the Temporal UI history. Between activities the workflow body runs
deterministically — pure orchestration with no side effects. The
`wait_condition` at the end is the durable pause: zero CPU while waiting, no
polling, instant wake when the signal arrives.

The payoff is durability end-to-end. The same pipeline inside a Temporal
workflow records every model call and every tool call in workflow history, the
approval pause survives worker restarts, and the final output is reconstructable
from the audit log alone.

## Coming from LangGraph?

| LangGraph | Temporal (this lesson) |
|---|---|
| Three sub-graph nodes wired sequentially | Three `await agent.run(...)` calls in `@workflow.run` |
| Sub-graph state passed via the parent state schema | Return values of `agent.run` consumed directly as inputs |
| `interrupt(value)` raising `GraphInterrupt` | `await workflow.wait_condition(lambda: self._approved)` |
| `Command(resume=note)` posted to the API | `handle.signal(ResearchWorkflow.approve, note)` |
| `state.values["draft"]` read from the checkpointer | `await handle.query(ResearchWorkflow.draft)` |
| Token-usage rolled up via `usage=ctx.usage` (Track 01 lesson 11) | Each agent's usage is its own; aggregation lives at the workflow level if you need it |

The conceptual shape is identical: a graph of specialists + a pause for review +
an external signal that resumes. The implementation differs in two ways —
Temporal enforces strict determinism inside `@workflow.run` (no `httpx.get`, no
`random()`, no `datetime.now()`), and the pause is persisted by the cluster, not
by your local checkpointer.

## Walk the code

### `agents/clarifier.py` — stage one

The clarifier is a plain `Agent` with no tools, wrapped in a `TemporalAgent`.
Note the **unique `name=`** — Temporal derives activity names from it, and the
workflow registers three agents, so a collision would break worker startup.

```python
_base = Agent(
    model=FLASH,
    name="capstone_clarifier",
    instructions=(
        "You turn vague topics into ONE specific, researchable question. "
        "Reply with just the question — no preamble, no explanation. "
        "Keep it under 20 words."
    ),
)

clarifier = TemporalAgent(_base)
```

### `agents/researcher.py` — stage two

The researcher carries two tools registered with `@_base.tool_plain`. Hard-coded
fact tables (`_FACTS_GDP`, `_FACTS_POPULATION`) keep the lesson deterministic and
the test offline-safe; the production swap is a `WebSearch` capability or an HTTP
tool.

```python
@_base.tool_plain
def gdp(country: str) -> str:
    """Return GDP for a country (hardcoded reference data)."""
    return _FACTS_GDP.get(country, f"No GDP data for {country}")
```

`TemporalAgent(_base)` wraps **after** both tools are registered — the wrapper
inspects the toolset at construction time to lift each tool into its own
activity.

```python
# Wrap AFTER tools are registered. TemporalAgent inspects the toolset to
# lift each tool into its own activity at worker startup.
researcher = TemporalAgent(_base)
```

### `agents/writer.py` — stage three

The writer mirrors the clarifier: a tool-free `Agent` wrapped in a
`TemporalAgent`, so the whole stage runs as a single `model_request` activity.
`agents/__init__.py` re-exports all three so callers can write
`from agents import clarifier, researcher, writer`.

### `workflow.py` — the workflow class

**`ResearchWorkflow` declares `__pydantic_ai_agents__`** as a class attribute
listing all three agents. The plugin walks this list at worker startup and
registers each agent's auto-generated activities (a `model_request` plus every
tool). All three must be listed — anything left off never gets its activities
registered.

```python
@workflow.defn
class ResearchWorkflow(PydanticAIWorkflow):
    """Three-agent research pipeline with HITL approval at the end."""

    __pydantic_ai_agents__ = [clarifier, researcher, writer]
```

**`ResearchWorkflow.__init__`** sets the signal-visible state. It runs on every
workflow start *and* on replay, so state lives here, not as class attributes.

```python
def __init__(self) -> None:
    self._approved: bool = False
    self._approval_payload: str = ""
    self._draft: str = ""
    self._status: str = "starting"
```

**The `approve` signal handler** is sync by Temporal convention — it mutates
state and returns; the workflow body reacts via `wait_condition`.

```python
@workflow.signal
def approve(self, payload: str = "") -> None:
    self._approval_payload = payload
    self._approved = True
```

**The `draft` and `status` query handlers** are sync reads of `self`. They drive
the FastAPI front-end in Lesson 11 — `status()` powers `GET /research/{id}`.

```python
@workflow.query
def status(self) -> str:
    """Return the current pipeline stage."""
    return self._status
```

**The `run` body** is three sequential `await agent.run(...)` calls, each
preceded by a `self._status` update so a live query can report progress. Each
call lands `1–N` activities in history depending on tool usage.

```python
self._status = "clarifying"
clarified = await clarifier.run(
    f"Reformulate this topic into a single researchable question: {topic}"
)

self._status = "researching"
research = await researcher.run(clarified.output)

self._status = "writing"
drafted = await writer.run(
    f"Write a short report based on these findings: {research.output}"
)
self._draft = drafted.output
```

The final stage is the **HITL gate** — `workflow.wait_condition(lambda:
self._approved)`. The durable pause: zero CPU while waiting, instant wake when
`approve` flips the flag. Once released, the body appends the reviewer note (if
any) and returns the report.

```python
self._status = "awaiting_approval"
await workflow.wait_condition(lambda: self._approved)
self._status = "completed"
feedback = (
    f" [reviewer note: {self._approval_payload}]"
    if self._approval_payload
    else ""
)
return f"{drafted.output}{feedback}"
```

### `worker.py` — the worker process

Same shape as every other lesson's worker: one workflow to register.
`ResearchWorkflow` itself declares the three agents via `__pydantic_ai_agents__`,
and the plugin registers their activities at startup — no activity list to pass.

```python
await run_worker(workflows=[ResearchWorkflow])
```

### `starter.py` — the client

`start_workflow` returns a **handle** immediately — the workflow is now running
on the worker. The client sleeps 5 seconds (your window to open the UI and watch
the pause), then signals `approve` and awaits the result.

```python
handle = await client.start_workflow(
    ResearchWorkflow.run,
    "the economy of Japan",
    id=workflow_id,
    task_queue=TASK_QUEUE,
)
await asyncio.sleep(5)
await handle.signal(ResearchWorkflow.approve, "looks good, ship it")
result = await handle.result()
```

## Run it

Two terminals. Server up first (`make temporal-up`, leave running):

```bash
# Terminal A — worker (Ctrl-C to stop)
make temporal-10-worker
```

```bash
# Terminal B — starter (auto-approves after 5s)
make temporal-10
```

Expected: the starter prints a workflow id + UI URL, sleeps 5s, sends the
approval signal, then prints a 3–4 sentence report with `[reviewer note: looks
good, ship it]` appended.

Open the UI link and click through to **History**. You'll see 5–7 activity
scheduled/completed pairs (one model call per agent, plus tool calls in the
researcher stage), interleaved with `WorkflowTaskCompleted` events for the
orchestration in between. The `Signal received` event near the end marks where
`wait_condition` unblocked.

## Try it

1. **Watch the pause live.** Re-run the starter, then in a third terminal:
   ```bash
   temporal workflow query \
     --workflow-id <id-from-starter> \
     --type status \
     --namespace learn-pydantic-ai
   ```
   Run that during the 5-second window. You should see `clarifying`, then
   `researching`, then `writing`, then `awaiting_approval`.

2. **Manual approval.** Comment out the `await handle.signal(...)` line in
   `starter.py` and re-run. The workflow hangs on the `wait_condition`. Send the
   signal yourself:
   ```bash
   temporal workflow signal \
     --workflow-id <id> \
     --name approve \
     --input '"manual approval"' \
     --namespace learn-pydantic-ai
   ```

3. **Add a fourth stage.** Build a `critic` agent that scores the writer's draft
   on a 1–5 scale and returns a `CriticReport`. Have the workflow loop back to
   the writer if the score is < 3 (max 3 retries). Each loop iteration adds
   another set of activities to history.

## Gotchas

- **Unique `name=` per agent.** All three agents share the same task queue, so
  duplicate names produce duplicate activity registrations and the worker
  crashes at startup. `capstone_clarifier` / `capstone_researcher` /
  `capstone_writer`.
- **`TemporalAgent(...)` AFTER tool registration.** Wrap the base `Agent` only
  after all `@base.tool` / `@base.tool_plain` calls. The wrapper inspects the
  toolset at construction time.
- **Sub-package on `sys.path`.** The workflow does `from agents.clarifier import
  clarifier`. That only resolves because the Makefile's `temporal-10` and
  `temporal-10-worker` targets run the scripts with the lesson dir as
  `sys.path[0]`. Don't run the files from elsewhere without prepending the dir.
- **`workflow.wait_condition` blocks the whole workflow.** Putting one before
  the writer stage would pause clarification — fine if that's what you want, but
  every later activity is gated on the signal.

## Bridge

You can now compose multiple TemporalAgents into one durable, replayable
pipeline with a HITL gate — the capstone runs headlessly. [Lesson 11](../11_capstone_fastapi/README.md)
wraps the same workflow in a FastAPI service — `POST /research`, `GET
/research/{id}`, `POST /research/{id}/approve` — giving you the same shape as
`langgraph-api` but with Temporal underneath instead of a graph checkpointer.

## Pattern

*The canonical shape, for the re-read.*

```python
@workflow.defn
class ResearchWorkflow(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [clarifier, researcher, writer]

    def __init__(self) -> None:
        self._approved = False
        self._status = "starting"
        self._draft = ""

    @workflow.signal
    def approve(self, note: str = "") -> None: self._approved = True

    @workflow.query                                  # cheap live state read
    def status(self) -> str: return self._status

    @workflow.run
    async def run(self, topic: str) -> str:
        self._status = "clarifying"
        clarified = await clarifier.run(topic)
        self._status = "researching"
        research = await researcher.run(clarified.output)
        self._status = "writing"
        draft = await writer.run(research.output)
        self._draft = draft.output
        self._status = "awaiting_approval"
        await workflow.wait_condition(lambda: self._approved)
        return self._draft
```

Three agents, one workflow, one HITL gate. Each agent's `name=` becomes the
activity-name prefix in the UI.
