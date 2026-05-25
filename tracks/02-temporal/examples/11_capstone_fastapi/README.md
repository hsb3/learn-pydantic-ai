# Lesson 11 — Capstone: full production stack

> The code for this lesson is every file in this folder. Read this page top to
> bottom; it quotes the parts of the code you need to see. This is the only
> lesson that ships as a deployable stack rather than a minimal three-file
> example.

## Review

In [Lesson 10](../10_capstone_headless/README.md) you composed three agents —
clarifier → researcher → writer — plus a HITL approval gate inside one
headless durable workflow. This lesson takes that same multi-agent pipeline and
wraps it in a service.

## Goal

Build and ship the production-shaped artifact this whole track has been
pointing at: a durable multi-agent workflow with a long-running pre-fetch
activity, tuned retry policies, streaming events, HITL approval, Logfire
observability, and a FastAPI front-end — all packaged as a `docker compose`
stack you bring up with one command.

## Files in this lesson

Unlike every earlier lesson — a tidy directory of three files — this one is a
**deployable stack**. The extra files (`Dockerfile`, `docker-compose.yml`, an
`agents/` package, a demo script) are what turn a sample into a project.

| File | Role |
|---|---|
| `app.py` | The **FastAPI client surface** — five HTTP endpoints that start, poll, and signal the workflow. This replaces earlier lessons' `example.py` / `starter.py`: the *client role* is now a long-lived web service, not a one-shot script. |
| `worker.py` | The **worker process**. Configures Logfire, registers `CapstoneWorkflow` and `fetch_external_context`, installs `LogfirePlugin`. |
| `workflow.py` | Defines `CapstoneWorkflow`, the `@workflow.defn` class. The deterministic five-stage pipeline — the thing being taught. |
| `activities.py` | The `fetch_external_context` long-running activity with `activity.heartbeat()`. The **Lesson 08** contribution. |
| `schemas.py` | Pydantic request/response models FastAPI uses to validate JSON bodies and serialize responses. |
| `agents/` | A package of three `TemporalAgent`s — `clarifier.py`, `researcher.py`, `writer.py` — plus `__init__.py` re-exporting them. Each agent demonstrates one track concept. |
| `ui.py` | An optional Streamlit front-end — a thin HTTP client over `app.py`, knowing nothing about Temporal. |
| `demo.sh` | A shell script driving the whole stack end-to-end with `curl` (`make temporal-11-curl`). |
| `Dockerfile` | One image used by **both** the worker and the API container — compose overrides `command:` per role. |
| `docker-compose.yml` | Five services — Postgres, Temporal, Temporal UI, worker, API — one volume, one network. |
| `.dockerignore` | Trims the build context: only the capstone dir and `learn_pydantic_ai/` ship in the image. |

**Does Temporal require this layout? No** — same answer as every lesson. A
worker is a task-queue string and two lists of Python objects; where you put
the files is your choice. What's new here is that the *client role* graduated
from a script to a service, and the whole thing is containerized. Full
explanation: [Anatomy of a Temporal lesson](../../README.md#anatomy-of-a-temporal-lesson).

## How it works

You package the whole track — multi-agent workflow, long-running activity,
retry tiers, streaming, HITL, Logfire — behind a FastAPI service in a
`docker compose` stack. The single key mechanic is the one-command stack:
`make temporal-11-up` brings up Temporal + worker + API together, exposing the
durable workflow over plain HTTP endpoints.

This isn't a new concept. It's *all* the concepts. Every prior lesson taught
one knob; this lesson combines them into the shape you'd actually run in
production: containerized worker + API process, a dedicated Temporal namespace,
persistent storage, observability wired, environment-driven configuration. The
goal is for the final artifact to feel like a *project*, not a sample.

The runtime topology is five containers, one stack:

```
                     ┌──────────────┐
   HTTP client ───►  │  FastAPI api │
                     │   :8001      │
                     └──────┬───────┘
                            │ Temporal SDK
                            ▼
   ┌────────┐       ┌──────────────┐       ┌──────────────────────────┐
   │postgres│◄──────│  temporal    │◄──────│  worker process          │
   │  :5432 │       │  server :7233│       │  - CapstoneWorkflow      │
   └────────┘       │  UI    :8080 │       │  - fetch_external_context│
                    └──────────────┘       │  - LogfirePlugin         │
                                           └──────────────────────────┘
```

The `worker` and `api` containers are the **same image** with different
`command:` lines — they share the project's deps and source. Everything they
need to know about Temporal is in env vars (`TEMPORAL_ADDRESS`,
`TEMPORAL_NAMESPACE`); everything they need to know about model providers is in
`GOOGLE_API_KEY`.

The workflow itself is a five-stage pipeline:

```
   POST /research {topic} ──► start_workflow
                                  │
                                  ▼
            Stage 1: fetch_external_context activity   (Lesson 08)
                     - heartbeats every second
                     - timeout 2 min, heartbeat timeout 10s
                                  │
                                  ▼
            Stage 2: clarifier agent run               (Lessons 03, 05)
                     - activity_config: 3 retries with backoff
                                  │
                                  ▼
            Stage 3: researcher agent run              (Lessons 04, 05, 06)
                     - tools: gdp(), population()
                     - per-tool activity_config: 5s timeout
                     - event_stream_handler logs each event
                                  │
                                  ▼
            Stage 4: writer agent run                  (default config)
                                  │
                                  ▼
            Stage 5: workflow.wait_condition(_decision) (Lesson 07)
                                  │
              POST /research/{id}/{approve|revise|reject} ───┘
                                  │
                                  ▼
                            return final report
```

### What's in here from each lesson

This is the map worth keeping — every track concept and exactly where it lives
in the capstone:

| Concept | Lesson | Where it lives in the capstone |
|---|---|---|
| `TemporalAgent` + `PydanticAIWorkflow` | 03 | `workflow.py` — `CapstoneWorkflow` |
| `@agent.tool_plain` lifted to activities | 04 | `agents/researcher.py` — `gdp`, `population` |
| `activity_config` + `tool_activity_config` retry tiers | 05 | `agents/clarifier.py`, `agents/researcher.py` |
| `event_stream_handler` streams model + tool events | 06 | `agents/researcher.py` — `_log_events` |
| `@workflow.signal` + `workflow.wait_condition` HITL | 07 | `workflow.py` — `approve`/`revise`/`reject` + `wait_condition` |
| Long-running activity with `activity.heartbeat()` | 08 | `activities.py` — `fetch_external_context` |
| `LogfirePlugin` wired alongside `PydanticAIPlugin` | 09 | `worker.py` — `extra_plugins=[LogfirePlugin()]` |
| Multi-agent orchestration | 10 | `workflow.py` — `clarifier → researcher → writer` |

## Coming from langgraph-api?

| langgraph-sdk client call | Capstone endpoint |
|---|---|
| `client.threads.create() + client.runs.create(...)` | `POST /research {"topic": "..."}` |
| `client.runs.join(thread_id, run_id)` | `GET /research/{workflow_id}` (poll until `status=="completed"`) |
| `client.threads.get_state(thread_id).values` | `GET /research/{workflow_id}` exposes live `status` + `draft` via workflow queries |
| `client.runs.create(..., Command(resume=note))` | `POST /research/{workflow_id}/approve {"note": "..."}` |
| `thread_id` | `workflow_id` |
| LangSmith trace | Logfire trace |

The contract you expose to HTTP clients is identical. The implementation
underneath differs (Temporal workflow history vs LangGraph checkpointer) but a
caller can't tell.

## Walk the code

### `activities.py` — the long-running pre-fetch

**`fetch_external_context`** simulates a slow pre-research data fetch (5×1s
sleep) and heartbeats every iteration. This is **Lesson 08** in the capstone:
the heartbeat is what lets the worker be killed mid-fetch and have Temporal
reschedule the activity rather than silently drop the workflow.

```python
@activity.defn
async def fetch_external_context(topic: str) -> str:
    facts: list[str] = []
    for step in range(1, 6):
        activity.heartbeat(f"step {step}/5")
        await asyncio.sleep(1)
        facts.append(f"fact-{step}")
    return f"Pre-fetched context for '{topic}': " + ", ".join(facts)
```

### `agents/clarifier.py` — the base retry tier

`clarifier` is a `TemporalAgent` whose `activity_config` sets the **base**
retry policy applied to every activity this agent generates (the model request
itself). This is **Lesson 05**'s base tier — three attempts with exponential
backoff, `ValueError` made non-retryable so input-validation failures fail fast.

```python
clarifier = TemporalAgent(
    _base,
    activity_config={
        "start_to_close_timeout": timedelta(seconds=60),
        "retry_policy": RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_attempts=3,
            non_retryable_error_types=["ValueError"],
        ),
    },
)
```

### `agents/researcher.py` — tools, per-tool config, streaming

Three track concepts converge in one agent. **Lesson 04**: two lookup tools
registered with `@_base.tool_plain`:

```python
@_base.tool_plain
def gdp(country: str) -> str:
    """Return the GDP of a country."""
    return _GDP.get(country, f"No GDP data for {country}")
```

**Lesson 06**: `_log_events` is the `event_stream_handler`. It runs as a
Temporal activity, so `activity.logger` is the right sink — and Logfire picks
those up for free:

```python
async def _log_events(
    ctx: RunContext[None], stream: AsyncIterable[AgentStreamEvent]
) -> None:
    async for event in stream:
        kind = event.event_kind
        if kind == "part_delta":  # too noisy for production logs
            continue
        activity.logger.info("researcher event: %s", kind)
```

**Lesson 05**'s deepest tier: `tool_activity_config` overrides retry/timeout
*per tool*. Lookup tools are fast, so a tight 5s timeout makes a stuck
connection fail quickly and retry:

```python
researcher = TemporalAgent(
    _base,
    event_stream_handler=_log_events,
    activity_config={...},
    tool_activity_config={
        "<agent>": {
            "gdp": {
                "start_to_close_timeout": timedelta(seconds=5),
                "retry_policy": RetryPolicy(maximum_attempts=2),
            },
            "population": {...},
        },
    },
)
```

### `agents/writer.py` — the minimal agent

`writer = TemporalAgent(_base)` — no config. The retry/timeout defaults are
fine for a single forward-pass call with no tools.

### `workflow.py` — the five-stage durable pipeline

**`CapstoneWorkflow`** is a `@workflow.defn` class extending
`PydanticAIWorkflow`. The `__pydantic_ai_agents__` list is what the
`PydanticAIPlugin` walks at worker startup to register each agent's
auto-generated model and tool activities:

```python
@workflow.defn
class CapstoneWorkflow(PydanticAIWorkflow):
    __pydantic_ai_agents__ = [clarifier, researcher, writer]
```

**`__init__`** sets the per-instance state for the HITL gate and the live
queries — it re-runs on every replay, so it only assigns values:

```python
def __init__(self) -> None:
    self._decision: str | None = None  # "approve" | "revise" | "reject"
    self._feedback: str = ""
    self._approval_note: str = ""
    self._status: str = "starting"
    self._draft: str = ""
```

**`approve` / `revise` / `reject`** are the three `@workflow.signal` handlers —
the HITL gate from **Lesson 07**, now with three exit doors instead of one.
Each is sync and only mutates `self`:

```python
@workflow.signal
def approve(self, note: str = "") -> None:
    self._approval_note = note
    self._decision = "approve"
```

**`status` and `draft`** are `@workflow.query` handlers — sync reads the
FastAPI layer polls to expose live progress and the in-flight draft.

**`run`** is the body. Stage 1 kicks off the long activity directly (not via an
agent) — this is the **Lesson 08** wiring:

```python
context = await workflow.execute_activity(
    fetch_external_context,
    topic,
    start_to_close_timeout=timedelta(minutes=2),
    heartbeat_timeout=timedelta(seconds=10),
)
```

Stages 2–4 are three sequential `await <agent>.run(...)` calls — clarifier →
researcher → writer — exactly the **Lesson 10** multi-agent shape. Stage 5 is
the HITL gate, wrapped in a `while` loop so a `revise` decision can fold
feedback back into the writer and return to the gate. The loop exits only on
`approve` or `reject`:

```python
while True:
    self._decision = None
    self._status = "awaiting_approval"
    await workflow.wait_condition(lambda: self._decision is not None)

    if self._decision == "approve":
        self._status = "completed"
        return self._draft + note
    if self._decision == "reject":
        self._status = "rejected"
        return f"REJECTED — the reviewer closed this without shipping.{reason}"
    # "revise" — fold the feedback back into the writer, then re-review.
```

### `worker.py` — the worker process with observability

**`_configure_logfire`** runs *outside* workflow code, before the worker boots.
`LogfirePlugin()` rides in `extra_plugins=`. This is **Lesson 09** — Logfire is
a silent no-op when `LOGFIRE_TOKEN` is unset:

```python
async def main() -> None:
    _configure_logfire()
    await run_worker(
        workflows=[CapstoneWorkflow],
        activities=[fetch_external_context],
        extra_plugins=[LogfirePlugin()],
    )
```

`fetch_external_context` *must* be passed in `activities=` — it's not an
agent-generated activity, so the plugin won't register it for you.

### `app.py` — the FastAPI client surface

Five endpoints. `start_research` calls `client.start_workflow` and returns an
id immediately:

```python
@app.post("/research", response_model=ResearchHandle)
async def start_research(req: ResearchRequest) -> ResearchHandle:
    client = await connect()
    wf_id = f"research-{uuid.uuid4().hex[:8]}"
    await client.start_workflow(
        CapstoneWorkflow.run, req.topic, id=wf_id, task_queue=TASK_QUEUE,
    )
    return ResearchHandle(workflow_id=wf_id)
```

`get_research` reads the workflow with `describe()` and the two `query`
handlers — catching the narrow window where a just-started workflow hasn't
processed its first task yet. `approve_research`, `revise_research`, and
`reject_research` each forward one signal to the workflow handle. Every handler
opens a fresh client via `connect()` — fine for learning, see Gotchas.

### `docker-compose.yml` — five services, one image

`worker` and `api` both `build:` from the same `Dockerfile`; the `api` service
overrides `command:` to run `uvicorn app:app`. The `GOOGLE_API_KEY` env is
required (`${GOOGLE_API_KEY:?...}`), `LOGFIRE_TOKEN` is optional
(`${LOGFIRE_TOKEN:-}`). The `Dockerfile` builds from the repo root so it can
copy `learn_pydantic_ai/` and the capstone source into one image, installing
deps in a cacheable layer before the source.

## Run it

### One-command full stack (recommended)

```bash
# Make sure GOOGLE_API_KEY is in your shell or .env
make temporal-11-up        # build + bring up Temporal + worker + FastAPI

make temporal-11-curl      # scripted end-to-end demo
# OR drive manually:
open http://localhost:8001/docs

make temporal-11-logs      # follow worker + api stdout
make temporal-11-down      # stop everything (keep postgres volume)
make temporal-11-clean     # stop + wipe postgres
```

The `make temporal-11-curl` script (`demo.sh`) POSTs a topic, polls until
`awaiting_approval`, POSTs an approval, polls until `completed`, prints the
final report. End-to-end takes ~15 seconds.

### Local (no docker) — useful for iteration

If you want to edit code and re-run without rebuilding the image:

```bash
make temporal-up                # use the base track stack (Temporal only)
make temporal-11-worker         # worker locally
make temporal-11-api            # uvicorn with --reload
```

Then drive it the same way: `make temporal-11-curl` or open the Swagger UI.

### Live observability

Set `LOGFIRE_TOKEN` in `.env` and re-run. The worker container picks it up at
startup, instruments pydantic-ai + httpx, and streams traces. Click any
workflow in the Temporal UI, copy its workflow id, then search Logfire for
`attributes.workflow_id="research-..."` to see the matching trace tree.

## Try it

1. **Force a tool failure.** Edit `agents/researcher.py` so `gdp(country)`
   raises `RuntimeError("upstream rate-limited")` for `country == "Brazil"`.
   POST `{"topic": "Brazil"}`. Watch the Temporal UI — you'll see two
   `ActivityTaskFailed` events for the `gdp` tool before the per-tool retry
   policy (`maximum_attempts=2`) gives up, then the model recovers and tries
   something else.

2. **Force the workflow to outlast the worker.** With `make temporal-11-up`
   running, POST a topic. Once it's in `awaiting_approval`, run
   `docker compose -f tracks/02-temporal/examples/11_capstone_fastapi/docker-compose.yml restart worker`.
   The worker dies and restarts; the workflow stays paused. POST the
   approval — the new worker picks up where the old one left off. Durability,
   demonstrated.

3. **Drive the `revise` loop.** POST a topic, wait for `awaiting_approval`,
   then `POST /research/{id}/revise {"feedback": "..."}`. The workflow folds
   your feedback into the writer, produces a new draft, and returns to the same
   gate — a single durable run looping until you approve or reject.

4. **Stream tokens to the client.** Wire `GET /research/{id}/stream` as a
   server-sent-events endpoint. The `event_stream_handler` in the researcher
   already produces events — push them through an `asyncio.Queue` that the SSE
   handler drains. This is how `langgraph-sdk`'s `client.runs.stream(...)`
   works under the hood.

## Gotchas

- **`temporal-11-up` reads `GOOGLE_API_KEY` from your shell.** The compose file
  references `${GOOGLE_API_KEY:?GOOGLE_API_KEY must be set...}` — if it's only
  in `.env` and not exported, the `make` target sources `.env` before invoking
  compose. If you run compose directly, `source .env && docker compose ...`
  first or you'll see the friendly error.
- **The capstone stack and the base track stack share the host's port 7233 and
  8080.** Don't run both `make temporal-up` AND `make temporal-11-up` at the
  same time. `temporal-11-up` brings up its OWN Temporal+UI; tear down the base
  stack first if it's running.
- **`workflow.execute_activity(fetch_external_context, ...)` requires the
  activity to be registered on the worker.** `worker.py` passes it via
  `activities=[fetch_external_context]`. Forget that and the workflow hangs at
  stage 1 — no error, just no progress, because Temporal is waiting for a
  worker that can run the activity.
- **Each handler call in `app.py` opens a fresh client.** Cheap for learning,
  wasteful for production. Cache on `app.state.client` in a `lifespan` handler
  and reuse.
- **`response_model=ResearchStatus` enforces shape.** FastAPI drops any field
  not on the Pydantic model, so adding a debug field to the workflow query
  without updating `schemas.py` means it never reaches the client.
- **`docker compose build` rebuilds the image from scratch when you edit
  `learn_pydantic_ai/`.** That's intentional — the package is baked into the
  image. For tight iteration, prefer the local (`make temporal-11-worker` +
  `make temporal-11-api`) path; reach for the docker stack when you're
  verifying the deployable shape.

## Bridge

Track 02 ends here. You have a self-contained durable agent system —
multi-agent, observable, signal-driven, containerized, one-command up — that
uses every primitive from lessons 03-10. The pattern generalizes: more agents,
more tools, more endpoints, more docker services, but the same six concepts
(workflow, activity, signal, query, retry policy, plugin) cover all of it.

What's next is in [`../../README.md`](../../README.md)'s "What this track does
NOT cover (yet)" — production versioning (`workflow.patched()`),
`TemporalRunContext` subclassing, multi-tenant deployment. These build on what's
here rather than replacing it.

## Pattern

*The canonical shape, for the re-read.*

```bash
# Bring up the entire stack: Temporal + worker + FastAPI, all containerized.
make temporal-11-up

# Drive it end-to-end.
make temporal-11-curl                    # scripted demo
open http://localhost:8001/docs          # FastAPI Swagger UI
open http://localhost:8080               # Temporal UI

# Tear down (keeps postgres volume; use `temporal-11-clean` to wipe).
make temporal-11-down
```

The capstone composes every concept from the track into one durable workflow
behind a `docker compose` stack. Single command up, single command down, real
workflow history visible in the Temporal UI, real Logfire traces if
`LOGFIRE_TOKEN` is set.
