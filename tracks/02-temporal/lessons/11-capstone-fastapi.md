# Lesson 11 — Capstone: full production stack

**Code:** `../examples/11_capstone_fastapi/`

## Review

- In Lesson 10 you composed three agents (clarifier → researcher →
  writer) plus a HITL approval gate inside one headless durable workflow
  — the multi-agent pipeline this lesson wraps in a service.

## Goal

Build and ship the production-shaped artifact this whole track has been pointing at: a durable multi-agent workflow with a long-running pre-fetch activity, tuned retry policies, streaming events, HITL approval, Logfire observability, and a FastAPI front-end — all packaged as a `docker compose` stack you bring up with one command.

## TL;DR

You package the whole track — multi-agent workflow, long-running activity,
retry tiers, streaming, HITL, Logfire — behind a FastAPI service in a
`docker compose` stack. The single key mechanic is the one-command stack:
`make temporal-11-up` brings up Temporal + worker + API together, exposing
the durable workflow over plain HTTP endpoints. The canonical shape is in [Pattern](#pattern).

## Why it matters

Every prior lesson taught one knob. This lesson combines all of them into the shape you'd actually run in production: containerized worker + API process, dedicated Temporal namespace, persistent storage, observability wired, environment-driven configuration. The goal is for the final artifact to feel like a *project*, not a sample.

## What's in here from each lesson

| Concept | Lesson | Where it lives in the capstone |
|---|---|---|
| `TemporalAgent` + `PydanticAIWorkflow` | 03 | `workflow.py` — `CapstoneWorkflow` |
| `@agent.tool_plain` lifted to activities | 04 | `agents/researcher.py` — `gdp`, `population` |
| `activity_config` + `tool_activity_config` retry tiers | 05 | `agents/clarifier.py`, `agents/researcher.py` |
| `event_stream_handler` streams model + tool events | 06 | `agents/researcher.py` — `_log_events` |
| `@workflow.signal` + `workflow.wait_condition` HITL | 07 | `workflow.py` — `approve` + `wait_condition` |
| Long-running activity with `activity.heartbeat()` | 08 | `activities.py` — `fetch_external_context` |
| `LogfirePlugin` wired alongside `PydanticAIPlugin` | 09 | `worker.py` — `extra_plugins=[LogfirePlugin()]` |
| Multi-agent orchestration | 10 | `workflow.py` — `clarifier → researcher → writer` |

This isn't a new concept. It's *all* the concepts.

## Mental model

The runtime topology:

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

Five containers, one stack. The `worker` and `api` containers are the same image with different `command:` lines — they share the project's deps and source. Everything they need to know about Temporal is in env vars (`TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`); everything they need to know about model providers is in `GOOGLE_API_KEY`.

The workflow itself:

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
            Stage 5: workflow.wait_condition(_approved) (Lesson 07)
                                  │
                       POST /research/{id}/approve ───┘
                                  │
                                  ▼
                            return final report
```

## Coming from langgraph-api?

| langgraph-sdk client call | Capstone endpoint |
|---|---|
| `client.threads.create() + client.runs.create(...)` | `POST /research {"topic": "..."}` |
| `client.runs.join(thread_id, run_id)` | `GET /research/{workflow_id}` (poll until `status=="completed"`) |
| `client.threads.get_state(thread_id).values` | `GET /research/{workflow_id}` exposes live `status` + `draft` via workflow queries |
| `client.runs.create(..., Command(resume=note))` | `POST /research/{workflow_id}/approve {"note": "..."}` |
| `thread_id` | `workflow_id` |
| LangSmith trace | Logfire trace |

The contract you expose to HTTP clients is identical. The implementation underneath differs (Temporal workflow history vs LangGraph checkpointer) but a caller can't tell.

## Walk the code

- `activities.py` — `fetch_external_context` simulates a slow pre-fetch (5×1s sleep) with `activity.heartbeat()` each iteration. This is **Lesson 08** in the capstone.
- `agents/clarifier.py:24` — `TemporalAgent(_base, activity_config={...})` sets the **base** retry policy. This is **Lesson 05**'s base tier.
- `agents/researcher.py:73` — `event_stream_handler=_log_events`. Each model + tool event flows through this handler. The handler runs as a Temporal activity, so it can call `activity.logger.info(...)` freely. This is **Lesson 06** plus **Lesson 09** wiring.
- `agents/researcher.py:82` — `tool_activity_config={"<agent>": {"gdp": {...}, "population": {...}}}` sets **per-tool** retry. This is **Lesson 05**'s deepest tier.
- `workflow.py:75` — `await workflow.execute_activity(fetch_external_context, ..., heartbeat_timeout=...)`. The workflow body kicks off the long activity, not via an agent. This is **Lesson 08** wiring.
- `workflow.py:91` — three sequential `await <agent>.run(...)` calls — clarifier → researcher → writer — exactly like **Lesson 10**.
- `workflow.py:111` — `await workflow.wait_condition(lambda: self._approved)` is the HITL gate from **Lesson 07**.
- `worker.py:38` — `_configure_logfire()` runs OUTSIDE workflow code, before the worker boots. `LogfirePlugin()` rides in `extra_plugins=`. This is **Lesson 09**.
- `app.py:38` — the three FastAPI endpoints: `start_workflow`, `query`, `signal`.
- `docker-compose.yml` — five services, one volume, one network. `worker` and `api` build from the same `Dockerfile`.

## Run

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

The `make temporal-11-curl` script POSTs a topic, polls until `awaiting_approval`, POSTs an approval, polls until `completed`, prints the final report. End-to-end takes ~15 seconds.

### Local (no docker) — useful for iteration

If you want to edit code and re-run without rebuilding the image:

```bash
make temporal-up                # use the base track stack (Temporal only)
make temporal-11-worker         # worker locally
make temporal-11-api            # uvicorn with --reload
```

Then drive it the same way: `make temporal-11-curl` or open the Swagger UI.

### Live observability

Set `LOGFIRE_TOKEN` in `.env` and re-run. The worker container will pick it up at startup, instrument pydantic-ai + httpx, and stream traces. Click any workflow in the Temporal UI, copy its workflow id, then search Logfire for `attributes.workflow_id="research-..."` to see the matching trace tree.

## Try it

1. **Force a tool failure.** Edit `agents/researcher.py` so `gdp(country)` raises `RuntimeError("upstream rate-limited")` for `country == "Brazil"`. POST `{"topic": "Brazil"}`. Watch the Temporal UI — you'll see two `ActivityTaskFailed` events for the `gdp` tool before the per-tool retry policy (`maximum_attempts=2`) gives up, then the model recovers and tries something else.

2. **Force the workflow to outlast the worker.** With `make temporal-11-up` running, POST a topic. Once it's in `awaiting_approval`, run `docker compose -f tracks/02-temporal/examples/11_capstone_fastapi/docker-compose.yml restart worker`. The worker dies and restarts; the workflow stays paused. POST the approval — the new worker picks up where the old one left off. Durability, demonstrated.

3. **Add `POST /research/{id}/reject`.** Mirror the `approve` shape but flip the signal handler to set `_rejected=True`. Branch the `wait_condition` predicate to wake on either signal, and branch the return on which fired. The workflow stays a single durable run with two exit doors.

4. **Stream tokens to the client.** Wire `GET /research/{id}/stream` as a server-sent-events endpoint. The `event_stream_handler` in the researcher already produces events — push them through a `asyncio.Queue` that the SSE handler drains. This is how `langgraph-sdk`'s `client.runs.stream(...)` works under the hood.

## Gotchas

- **`temporal-11-up` reads `GOOGLE_API_KEY` from your shell.** The compose file references `${GOOGLE_API_KEY:?GOOGLE_API_KEY must be set}` — if it's only in `.env` and not exported, the `make` target sources `.env` before invoking compose. If you run compose directly, `source .env && docker compose ...` first or you'll see the friendly error.
- **The capstone stack and the base track stack share the host's port 7233 and 8080.** Don't run both `make temporal-up` AND `make temporal-11-up` at the same time. `temporal-11-up` brings up its OWN Temporal+UI; tear down the base stack first if it's running.
- **`workflow.execute_activity(fetch_external_context, ...)` requires the activity to be registered on the worker.** `worker.py` passes it via `activities=[fetch_external_context]`. Forget that and the workflow hangs at stage 1 — no error, just no progress, because Temporal is waiting for a worker that can run the activity.
- **Each handler call in `app.py` opens a fresh client.** Cheap for learning, wasteful for production. Cache on `app.state.client` in a `lifespan` handler and reuse.
- **`response_model=ResearchStatus` enforces shape.** FastAPI drops any field not on the Pydantic model, so adding a debug field to the workflow query without updating `schemas.py` means it never reaches the client.
- **`docker compose build` rebuilds the image from scratch when you edit `learn_pydantic_ai/`.** That's intentional — the package is baked into the image. For tight iteration, prefer the local (`make temporal-11-worker` + `make temporal-11-api`) path; reach for the docker stack when you're verifying the deployable shape.

## Bridge

Track 02 ends here. You have a self-contained durable agent system — multi-agent, observable, signal-driven, containerized, one-command up — that uses every primitive from lessons 03-10. The pattern generalizes: more agents, more tools, more endpoints, more docker services, but the same six concepts (workflow, activity, signal, query, retry policy, plugin) cover all of it.

What's next is in [`../README.md`](../README.md)'s "What this track does NOT cover (yet)" — production versioning (`workflow.patched()`), `TemporalRunContext` subclassing, multi-tenant deployment. These build on what's here rather than replacing it.

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

The capstone composes every concept from the track into one durable workflow behind a `docker compose` stack. Single command up, single command down, real workflow history visible in the Temporal UI, real Logfire traces if `LOGFIRE_TOKEN` is set.
