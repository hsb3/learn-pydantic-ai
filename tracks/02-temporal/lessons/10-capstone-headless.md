# Lesson 10 — Capstone: headless research workflow

**Code:** `../examples/10_capstone_headless/`

## Review

- In Lesson 09 you wired `LogfirePlugin` so every workflow execution
  became a trace tree of model, tool, and HTTP spans — correlated with
  the Temporal history you see in the UI.

## Goal

Compose **three TemporalAgents** — a clarifier, a researcher, and a writer
— inside a single durable workflow that pauses for human approval before
returning. This is the multi-agent + HITL pattern you've been building
toward since Lesson 03. Everything in the track converges here.

## TL;DR

You compose three agents — clarifier → researcher → writer — as
sequential `await agent.run(...)` calls inside one `PydanticAIWorkflow`,
then gate the return on a HITL approval. The single key mechanic is that
`__pydantic_ai_agents__ = [...]` registers all three (each agent's `name=`
becoming its activity-name prefix) while a final `workflow.wait_condition`
holds the durable pause. The canonical shape is in [Pattern](#pattern).

## Why it matters

Real production agents almost never run as a single model call. They
fan out into specialists (each with focused prompts and small tool
surfaces) and route through review steps before any irreversible action.
Doing that on raw asyncio gives you no resilience — a crash mid-pipeline
loses the work in flight. The same pipeline inside a Temporal workflow
is durable end-to-end: every model call and every tool call lands in
workflow history, the approval pause survives worker restarts, and the
final output is reconstructable from the audit log alone.

## Mental model

```
   topic ───► clarifier ───► researcher ───► writer ───► [HITL] ───► report
              (model)     (model + tools)    (model)     (signal)
              activity      activities       activity     pause
```

Each `await agent.run(...)` line in the workflow is one or more activity
scheduling events in the Temporal UI history. Between activities the
workflow body itself runs deterministically — pure orchestration with no
side effects. The `wait_condition` at the end is the durable pause: zero
CPU while waiting, no polling, instant wake when the signal arrives.

## Coming from LangGraph?

| LangGraph | Temporal (this lesson) |
|---|---|
| Three sub-graph nodes wired sequentially | Three `await agent.run(...)` calls in `@workflow.run` |
| Sub-graph state passed via the parent state schema | Return values of `agent.run` consumed directly as inputs |
| `interrupt(value)` raising `GraphInterrupt` | `await workflow.wait_condition(lambda: self._approved)` |
| `Command(resume=note)` posted to the API | `handle.signal(ResearchWorkflow.approve, note)` |
| `state.values["draft"]` read from the checkpointer | `await handle.query(ResearchWorkflow.draft)` |
| Token-usage rolled up via `usage=ctx.usage` (Track 01 lesson 11) | Each agent's usage is its own; aggregation lives at the workflow level if you need it |

The conceptual shape is identical: a graph of specialists + a pause for
review + an external signal that resumes. The implementation differs in
two ways — Temporal enforces strict determinism inside `@workflow.run`
(no `httpx.get`, no `random()`, no `datetime.now()`), and the pause is
persisted by the cluster, not by your local checkpointer.

## Walk the code

- `agents/clarifier.py:18` — `Agent(model=FLASH, name="capstone_clarifier", ...)`.
  Note the **unique `name=`** — Temporal derives activity names from it
  and the workflow registers three agents, so collisions would break
  worker startup.
- `agents/researcher.py:39` — `@_base.tool_plain` for `gdp` and
  `population`. Hard-coded data keeps the lesson deterministic and the
  test offline-safe; the production swap is a `WebSearch` capability
  or an HTTP tool.
- `agents/researcher.py:53` — `TemporalAgent(_base)` wraps **after**
  the tools are registered. The wrapper inspects the toolset at
  construction time.
- `workflow.py:36` — `__pydantic_ai_agents__ = [clarifier, researcher, writer]`.
  All three must be listed; the plugin walks this list at worker startup.
- `workflow.py:53` / `workflow.py:67` — `@workflow.signal approve(...)`
  (sync) and `@workflow.query status() / draft()`. The query methods
  drive the FastAPI front-end in Lesson 11.
- `workflow.py:77` — three sequential `await agent.run(...)` calls. Each
  one lands `1-N` activities in history depending on tool usage.
- `workflow.py:96` — `await workflow.wait_condition(lambda: self._approved)`.
  The durable pause.

## Run

Two terminals. Server up first (`make temporal-up`, leave running):

```bash
# Terminal A — worker (Ctrl-C to stop)
make temporal-10-worker
```

```bash
# Terminal B — starter (auto-approves after 5s)
make temporal-10
```

Expected: the starter prints a workflow id + UI URL, sleeps 5s, sends
the approval signal, then prints a 3-4 sentence report with `[reviewer
note: looks good, ship it]` appended.

Open the UI link and click through to **History**. You'll see 5-7
activity scheduled/completed pairs (one model call per agent, plus tool
calls in the researcher stage), interleaved with `WorkflowTaskCompleted`
events for the orchestration in between. The `Signal received` event
near the end marks where `wait_condition` unblocked.

## Try it

1. **Watch the pause live.** Re-run the starter, then in a third terminal:
   ```bash
   temporal workflow query \
     --workflow-id <id-from-starter> \
     --type status \
     --namespace learn-pydantic-ai
   ```
   Run that during the 5-second window. You should see `clarifying`,
   then `researching`, then `writing`, then `awaiting_approval`.

2. **Manual approval.** Comment out the `await handle.signal(...)`
   line in `starter.py` and re-run. The workflow hangs on the
   `wait_condition`. Send the signal yourself:
   ```bash
   temporal workflow signal \
     --workflow-id <id> \
     --name approve \
     --input '"manual approval"' \
     --namespace learn-pydantic-ai
   ```

3. **Add a fourth stage.** Build a `critic` agent that scores the
   writer's draft on a 1-5 scale and returns a `CriticReport`. Have the
   workflow loop back to the writer if the score is < 3 (max 3 retries).
   Each loop iteration adds another set of activities to history.

## Gotchas

- **Unique `name=` per agent.** All three agents share the same task
  queue, so duplicate names produce duplicate activity registrations
  and the worker crashes at startup. `capstone_clarifier` /
  `capstone_researcher` / `capstone_writer`.
- **`TemporalAgent(...)` AFTER tool registration.** Wrap the base
  `Agent` only after all `@base.tool` / `@base.tool_plain` calls. The
  wrapper inspects the toolset at construction time.
- **Sub-package on `sys.path`.** The workflow does `from agents.clarifier
  import clarifier`. That only resolves because the Makefile's
  `temporal-10` and `temporal-10-worker` targets run the scripts with
  the lesson dir as `sys.path[0]`. Don't run the files from elsewhere
  without prepending the dir.
- **`workflow.wait_condition` blocks the whole workflow.** Putting one
  before the writer stage would pause clarification — fine if that's
  what you want, but every later activity is gated on the signal.

## Bridge

The capstone runs headlessly. Lesson 11 wraps the same workflow in a
FastAPI service — `POST /research`, `GET /research/{id}`, `POST
/research/{id}/approve` — giving you the same shape as `langgraph-api`
but with Temporal underneath instead of a graph checkpointer.

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

Three agents, one workflow, one HITL gate. Each agent's `name=` becomes the activity-name prefix in the UI.
