# Track 02 — Durable agents with Temporal

Run pydantic-ai agents inside Temporal workflows so they survive crashes,
retries, and long human-in-the-loop pauses. 11 lessons, 6 sections, from
"never touched Temporal" to "your own server running a multi-agent durable
workflow behind a FastAPI front-end."

Each lesson is a **self-contained directory** under `lessons/`. Open the
folder and its `README.md` is the lesson — the narrative sits right next to
the code it explains. There is no separate `lessons/` tree to cross-reference.

## The arc

The 11 lessons are grouped into 6 sections. Each section has its own payoff —
you can stop after any section and have something useful. Section 4 is
**optional**: Logfire is the cherry on top, not a prerequisite for the
capstone.

| Section | Lessons | What you'll be able to do |
|:------|---------|---------------------------|
| **0 — Foundations: server + the workflow class** | 01, 02 | Bring up your own Postgres-backed Temporal stack via docker-compose. Recognize the building blocks (workflow, activity, worker, task queue, signal, query) and learn *why a workflow is a class* — state on `self`, `@workflow.signal`, `@workflow.query`, `wait_condition` — all in plain Temporal, no agent yet. |
| **1 — Your first durable agent** | 03, 04 | Run a Pydantic AI agent inside a Temporal workflow. See exactly which calls become **activities** (durable, retryable) vs which stay in the **workflow** (deterministic orchestration). |
| **2 — Configuration & resilience** | 05, 06 | Tune `ActivityConfig` — timeouts, retry policies, per-tool overrides. Stream model + tool events out of a workflow with `event_stream_handler`. |
| **3 — Long pauses & long work** | 07, 08 | Pause workflows for human approval (signals + `workflow.wait_condition`). Heartbeat long-running activities so the cluster knows they're alive. |
| **4 — Production polish (optional)** | 09 | Wire `LogfirePlugin` to correlate Temporal workflow history with span-level traces. Skippable without a Logfire account. |
| **5 — Capstone** | 10, 11 | A multi-agent research workflow (clarifier → researcher → writer) with HITL approval. Then put a FastAPI front-end on it — the langgraph-api analogue you already know. |

## Lesson index

| # | Lesson | Concept |
|---|--------|---------|
| 01 | [Temporal in 15 minutes](lessons/01_temporal_tour/README.md) | Temporal primitives + bring up your server (notebook) |
| 02 | [A workflow is a class](lessons/02_stateful_workflow/README.md) | `__init__` state, `@workflow.signal`, `@workflow.query`, `wait_condition` — plain Temporal, no agent yet |
| 03 | [Hello durable agent](lessons/03_hello_durable/README.md) | `TemporalAgent` + `PydanticAIWorkflow` end-to-end |
| 04 | [Workflow vs activity boundary](lessons/04_workflow_vs_activity/README.md) | Read the Temporal history — what's an activity, what isn't |
| 05 | [Tuning retries & timeouts](lessons/05_activity_config/README.md) | Retries, timeouts, per-tool `ActivityConfig` |
| 06 | [Streaming events](lessons/06_streaming/README.md) | `event_stream_handler` — streaming inside a durable workflow |
| 07 | [Human-in-the-loop with signals](lessons/07_hitl_approval/README.md) | `@workflow.signal` + `workflow.wait_condition` gating an agent |
| 08 | [Long-running activities](lessons/08_long_running/README.md) | Activity heartbeats, `start_to_close_timeout` |
| 09 | [Observability with Logfire](lessons/09_observability/README.md) | `LogfirePlugin` for trace correlation |
| 10 | [Capstone: headless research workflow](lessons/10_capstone_headless/README.md) | Multi-agent workflow (clarifier → researcher → writer) with HITL approval |
| 11 | [Capstone: full production stack](lessons/11_capstone_fastapi/README.md) | docker-compose stack (Temporal + worker + FastAPI) pulling in lessons 03–10 |

Work through them in order — each lesson's **Review** recalls the one mechanic
from the previous lesson you need in hand, and its **Bridge** sets up the next.

## Prerequisites

- Done Track 01 lessons 02–09 (you know `Agent`, tools, deps, capabilities).
- `docker` and `docker compose` working (`docker compose version` returns).
- `temporal` CLI on PATH — installed by `brew install temporal` (verify with
  `temporal --version`).
- `.env` with `GOOGLE_API_KEY` (lesson 03 onwards — lessons 01–02 are plain
  Temporal and need no model) and `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` for
  the capstone.
- (Optional) A Logfire account for Lesson 09 — free tier is fine.

## Anatomy of a Temporal lesson

**Temporal does not require any file or folder layout.** A worker is created
with `Worker(client, task_queue="...", workflows=[SomeClass],
activities=[some_fn])` — a task-queue string and two lists of Python objects.
Workflows are classes decorated with `@workflow.defn`; activities are functions
decorated with `@activity.defn`. Where you define them — one file or twenty —
is entirely your choice. A whole Temporal app can be a single `.py`.

What a running Temporal app genuinely needs is **three roles** — and they are
roles, not files:

1. **Workflow definition** — the `@workflow.defn` class. Deterministic
   orchestration code.
2. **Worker** — a long-lived *process* that connects to the server, polls a
   task queue, and runs whatever workflow/activity code it was given.
3. **Client / starter** — a *process* that tells the server "run workflow X"
   and optionally signals or queries it.

Lessons 02–09 put each role in its own file — `workflows.py`, `worker.py`,
`example.py` — for two reasons, both pedagogical or operational, neither a
Temporal rule:

- **The two-terminal study loop.** You run the worker in terminal A and the
  starter in terminal B to watch both sides at once. That needs two
  independently runnable entry points — hence two files with
  `if __name__ == "__main__"`.
- **The one real constraint: workflow modules must be import-safe.** Temporal's
  workflow sandbox *re-imports* your workflow module to reconstruct state
  during replay. If that module does I/O at import time (opens a file, hits the
  network, reads a clock), replay diverges from recorded history. Keeping the
  workflow class alone in `workflows.py`, with no top-level side effects, makes
  import-safety easy to guarantee. The worker and starter files *do* have side
  effects — which is the reason they are kept *out* of the workflow module.

So: `workflows.py` is separate because of a genuine Temporal constraint
(import-safety). `worker.py` and `example.py` are separate because the study
loop wants two terminals. None of the three filenames is mandated by Temporal;
a production app might bundle the worker with its workflows and ship the client
as a separate service — which is exactly what the Lesson 11 capstone does.

**What varies across lessons.** Lesson 01 is a single self-contained notebook
(it uses an in-process server, so it needs no worker terminal). Lessons that
need extra code add files — `flaky_tool.py` (05), `scraper.py` (08),
`activities.py` and an `agents/` package (10–11). The capstones use
`workflow.py` (singular) and `starter.py` / `app.py` instead of `example.py`.
Every lesson's **Files in this lesson** section names each file and its role,
so you never have to guess.

## How to study a lesson

1. **Read the README top to bottom: Review → Goal → Files → How it works.**
   The README quotes every part of the code you need to see; you rarely need
   to open the `.py` files separately while reading. The `## Pattern` block at
   the *bottom* is the cookbook for a months-later re-read — **skip it on a
   first pass**; it gives away the shape before you've built the mental model.
2. **Bring up the server** if not already running: `make temporal-up`. Verify
   with `make temporal-status` — should say `SERVING`. Open
   `http://localhost:8080`.
3. **Start the worker** in terminal A: `make temporal-NN-worker`. Leave it
   running — Ctrl-C kills it.
4. **Run the starter** in terminal B: `make temporal-NN`. Watch the worker
   logs in terminal A.
5. **Open the Temporal UI** at `http://localhost:8080` and click into the
   workflow that just ran. Inspect the history. **This is where the lightbulb
   moments happen** — you literally see which calls were durable.
6. **Modify** — every lesson has a "Try it" section. Tweak something, restart
   the worker, run again.
7. **Move on** when the "Bridge" section says what's next.

### The two-terminal pattern

You'll be in two terminals constantly for this track. Make your peace with it:

| Terminal A (worker) | Terminal B (starter / CLI) |
|---|---|
| `make temporal-02-worker` | `make temporal-02` |
| Hot-reload by Ctrl-C → re-run | Re-run as often as you like |
| Shows what the worker is doing | Shows what the starter is doing |

A real deployment runs the worker as a long-lived process (systemd, Docker,
k8s). For learning, your shell is the process manager. (Lesson 01 is the
exception — a self-contained notebook with no separate worker.)

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

```bash
# Terminal A — worker (leave running)
make temporal-02-worker

# Terminal B — starter
make temporal-02
```

Lesson 01 is a notebook — `make temporal-01` prints a pointer; open it in
VS Code or run `make nb-exec`.

Lesson 11 is the capstone and runs differently — it has its **own**
self-contained docker-compose stack (Temporal + worker + FastAPI all together):

```bash
make temporal-11-up         # build + bring up the whole capstone stack
make temporal-11-curl       # scripted end-to-end demo (POST → poll → approve → result)
make temporal-11-logs       # follow worker + api logs
make temporal-11-down       # stop (keeps postgres volume)
make temporal-11-clean      # stop + wipe postgres
```

For iterative local development without rebuilding the image, run
`make temporal-up` (base track stack) + `make temporal-11-worker` +
`make temporal-11-api` in three terminals instead. Don't run both stacks at
the same time — they fight over ports 7233 and 8080.

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
workflow sandbox passthrough list so `from learn_pydantic_ai import ...` works
inside workflow modules. Use it on every `Worker(...)` and in every test.
`run_worker()` does this for you automatically.

## Tests

```bash
make test-lessons-temporal       # all temporal lessons via WorkflowEnvironment.start_local()
                                  # No docker needed. Uses an ephemeral in-process server.
make test-against-local-server   # all lessons against your `make temporal-up` server
                                  # Use this to validate your docker stack.
```

The pre-push hook (`lefthook.yml` → `make test-live`) includes the
ephemeral-env tests.

## Self-hosted server architecture

The docker-compose stack at `docker/docker-compose.yml`:

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| postgresql | `postgres:13` | (internal) | Persistent store — survives container restarts via the `postgres-data` volume |
| temporal | `temporalio/auto-setup:1.27` | `7233` | Workflow + activity execution; bootstraps schema + namespace on first boot |
| temporal-ui | `temporalio/ui:2.36.0` | `8080` | Web UI for workflow history, signals, queries |

Default namespace: `learn-pydantic-ai`. Created automatically.

## Coming from LangGraph / langgraph-api?

The authoritative translation table lives in
[Lesson 03](lessons/03_hello_durable/README.md#coming-from-langgraph). Short
version:

- A Temporal `workflow` is a langgraph graph compiled with a checkpointer that
  gives you hard determinism + retries + signals for free.
- A Temporal `activity` is a graph node whose result is memoized to durable
  storage; pydantic-ai automatically lifts model + tool calls into activities.
- A `worker` + `task_queue` is langgraph-api's queue + worker pool.
- `workflow.wait_condition` is langgraph's `interrupt()`.
- A `signal` is a `Command(resume=...)` arriving over the network.

## Vocabulary you'll see repeatedly

- **Workflow** — the durable orchestrator. Code that survives crashes.
- **Activity** — a unit of side-effecting work invoked from a workflow.
  Retries automatically; the result is memoized.
- **Worker** — a process that polls a task queue and runs the workflow /
  activity code it finds.
- **Task queue** — the routing tier between client and worker. Everything in
  this track uses `learn-pydantic-ai`.
- **Signal** — an async message sent into a running workflow. Used for HITL.
- **Query** — a synchronous read of a running workflow's state.
- **Determinism** — workflow code re-runs to reconstruct state after a crash.
  No `random()`, no `datetime.now()`, no `httpx.get()` inside the workflow —
  put those in activities.

## What this track does NOT cover (yet)

The track gets you to a multi-agent durable workflow behind a FastAPI
front-end. To ship and *evolve* that in production, these are the next
chapters worth writing — in rough priority order:

1. **Workflow versioning with `workflow.patched()`** — once Lesson 10 ships,
   you cannot safely change `ResearchWorkflow` while runs are in flight without
   versioning. Critical for any "v1 → v2" deployment.
2. **`TemporalRunContext` subclassing** — by default only a small set of
   `RunContext` fields cross the activity boundary; richer deps (request
   context, multi-tenant identity, audit trails) need a subclassed
   `TemporalRunContext` with custom `serialize_run_context`.
3. **Production deployment** — Docker worker image, graceful drain, horizontal
   scaling via task queue topology, Temporal Cloud vs self-hosted trade-offs.
4. **`continue-as-new` in a real multi-agent loop** — Lesson 08 demonstrates
   the mechanic in isolation; a capstone-scale demo (e.g. a research workflow
   that processes a long topic stream) would close the loop.
5. **`provider_factory` / `models` kwarg on `TemporalAgent`** — runtime model
   switching and provider key injection from deps.
6. **Determinism deep dive** — [`docs/temporal/workflow-requirements.md`](../../docs/temporal/workflow-requirements.md)
   covers the determinism contract at a reference level; a "what actually
   breaks" appendix with intentionally-broken examples would still be valuable.
7. **Child workflows** — fan-out patterns via `execute_child_workflow`,
   sub-workflow ownership, propagating cancellations.
8. **`AgentPlugin`** — the single-agent alternative to declaring
   `__pydantic_ai_agents__` on a `PydanticAIWorkflow` subclass.

---

## Reference docs

Living reference material lives in [`docs/temporal/`](../../docs/temporal/):

- [`workflow-requirements.md`](../../docs/temporal/workflow-requirements.md) — what Temporal needs from your code (the four collaborators, determinism contract, pre-flight checklist).
- [`codec-server.md`](../../docs/temporal/codec-server.md) — the codec server explainer: encrypting payloads end-to-end, what the Web UI / CLI need to decode them.

---

*Authoring or reviewing a lesson?
[`docs/dev_docs/LESSON-DEVELOPMENT-GUIDE.md`](../../docs/dev_docs/LESSON-DEVELOPMENT-GUIDE.md)
is the living standard — lesson format, authoring rules, and the
quality-control checklist. The copy-paste skeleton is
[`docs/dev_docs/lesson-template.md`](../../docs/dev_docs/lesson-template.md).*
