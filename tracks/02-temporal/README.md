# Track 02 — Durable agents with Temporal

Run pydantic-ai agents inside Temporal workflows so they survive crashes,
retries, and long human-in-the-loop pauses. 11 lessons, ~6 phases, from
"never touched Temporal" to "your own server running a multi-agent durable
workflow behind a FastAPI front-end."

## Where to start

Read **[`lessons/00-orientation.md`](lessons/00-orientation.md)** first — it
explains the phases, the two-terminal study workflow, the vocabulary, and
the LangGraph translation. Then work through the numbered lessons.

## Lesson index

| # | Slug | Concept |
|---|------|---------|
| 01 | `01_temporal_tour` (notebook) | Temporal primitives + bring up your server |
| 02 | `02_stateful_workflow/` | A workflow is a class — `__init__` state, `@workflow.signal`, `@workflow.query`, `wait_condition` (plain Temporal, no agent yet) |
| 03 | `03_hello_durable/` | `TemporalAgent` + `PydanticAIWorkflow` end-to-end |
| 04 | `04_workflow_vs_activity/` | Read the Temporal history — what's an activity, what isn't |
| 05 | `05_activity_config/` | Retries, timeouts, per-tool `ActivityConfig` |
| 06 | `06_streaming/` | `event_stream_handler` — streaming inside a durable workflow |
| 07 | `07_hitl_approval/` | `@workflow.signal` + `workflow.wait_condition` for HITL (the L2 mechanics, now gating an agent) |
| 08 | `08_long_running/` | Activity heartbeats, `start_to_close_timeout` |
| 09 | `09_observability/` | `LogfirePlugin` for trace correlation |
| 10 | `10_capstone_headless/` | Multi-agent research workflow (clarifier → researcher → writer) with HITL approval |
| 11 | `11_capstone_fastapi/` | **Capstone**: docker-compose stack (Temporal + worker + FastAPI) that pulls in lessons 03-10 |

## Bring up your server

Lesson 01 walks through this in detail. Quick version:

```bash
make temporal-up         # docker compose up postgres + server + UI
make temporal-status     # cluster health check
make temporal-ui         # open http://localhost:8080
```

Tear-down: `make temporal-down` (keeps data) or `make temporal-clean` (wipes
the postgres volume — fresh slate).

## Running lessons

Each lesson is a **directory** containing `worker.py` + `example.py` (or
`starter.py` / `app.py`). The two-terminal pattern:

```bash
# Terminal A — worker (leave running)
make temporal-02-worker

# Terminal B — starter
make temporal-02
```

Lesson 11 is the capstone and runs differently — it has its **own**
self-contained docker-compose stack (Temporal + worker + FastAPI all
together):

```bash
make temporal-11-up         # build + bring up the whole capstone stack
make temporal-11-curl       # scripted end-to-end demo (POST → poll → approve → result)
make temporal-11-logs       # follow worker + api logs
make temporal-11-down       # stop (keeps postgres volume)
make temporal-11-clean      # stop + wipe postgres
```

For iterative local development without rebuilding the image, run
`make temporal-up` (base track stack) + `make temporal-11-worker` +
`make temporal-11-api` in three terminals instead. Don't run both stacks
at the same time — they fight over ports 7233 and 8080.

## Shared utilities (already wired)

All lessons import from the project-level package:

```python
from learn_pydantic_ai import (
    MODELS,            # {provider: {tier: model_string}}
    FLASH, PRO,        # google fast/smart aliases
    TASK_QUEUE,        # "learn-pydantic-ai" — every lesson uses this
    connect,           # async def connect() -> Client (PydanticAIPlugin pre-applied)
    run_worker,        # async def run_worker(workflows, activities=None, ...)
)
from learn_pydantic_ai.temporal import make_workflow_runner  # sandbox setup
```

`make_workflow_runner()` is critical — it adds `learn_pydantic_ai` to the
workflow sandbox passthrough list so `from learn_pydantic_ai import ...`
works inside workflow modules. Use it on every `Worker(...)` and in every
test. `run_worker()` does this for you automatically.

## Tests

```bash
make test-lessons-temporal       # all temporal lessons via WorkflowEnvironment.start_local()
                                  # No docker needed. Uses an ephemeral in-process server.
make test-against-local-server   # All lessons against your `make temporal-up` server
                                  # Use this to validate your docker stack.
```

The pre-push hook (`lefthook.yml` → `make test-live`) includes the
ephemeral-env tests.

## File-layout convention (departure from Track 01's flat layout)

```
examples/
  NN_<slug>/
    workflows.py     # or workflow.py (singular) for capstones
    worker.py
    example.py       # or starter.py
    [helpers].py     # tools, schemas, etc.
```

Each lesson is a multi-file unit (worker + starter at minimum). The
sub-directory keeps each lesson's files together and avoids polluting the
`examples/` namespace.

## Self-hosted server architecture

The docker-compose stack at `docker/docker-compose.yml`:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| postgresql | `postgres:13` | (internal) | Persistent store — survives container restarts via the `postgres-data` volume |
| temporal | `temporalio/auto-setup:1.27` | `7233` | Workflow + activity execution; bootstraps schema + namespace on first boot |
| temporal-ui | `temporalio/ui:2.36.0` | `8080` | Web UI for workflow history, signals, queries |

Default namespace: `learn-pydantic-ai`. Created automatically.

## What this track does NOT cover (yet)

The track gets you to a multi-agent durable workflow behind a FastAPI
front-end. To ship and *evolve* that in production, these are the next
chapters worth writing — listed in rough priority order so you (or a
future contributor) can pick them off:

1. **Workflow versioning with `workflow.patched()`** — once Lesson 10 ships,
   you cannot safely change `ResearchWorkflow` while runs are in flight
   without versioning. Critical for any "v1 → v2" deployment.
2. **`TemporalRunContext` subclassing** — by default only a small set of
   `RunContext` fields cross the activity boundary; richer deps (request
   context, multi-tenant identity, audit trails) need a subclassed
   `TemporalRunContext` with custom `serialize_run_context`.
3. **Production deployment** — Docker worker image, graceful drain,
   horizontal scaling via task queue topology, Temporal Cloud vs
   self-hosted trade-offs.
4. **`continue-as-new`** — full demo (Lesson 08 mentions it). Required for
   long-lived workflows that exceed the history-size limit.
5. **`provider_factory` / `models` kwarg on `TemporalAgent`** — runtime
   model switching (e.g., `agent.run(..., model="claude-haiku-4-5")`)
   and provider key injection from deps.
6. **Determinism deep dive** — a standalone appendix on what the sandbox
   blocks and why, with concrete "what breaks" examples. Lesson 04's
   gotchas touch this; a longer treatment would help.
7. **Child workflows** — fan-out patterns via `execute_child_workflow`,
   sub-workflow ownership, propagating cancellations.
8. **`AgentPlugin`** — the single-agent alternative to declaring
   `__pydantic_ai_agents__` on a `PydanticAIWorkflow` subclass.
