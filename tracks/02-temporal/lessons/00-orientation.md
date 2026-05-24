# Orientation

## The arc

The **11** lessons are grouped into **6** sections. Each section has its own
payoff — you can stop after any section and have something useful. Section 4 is
**optional**: Logfire is the cherry on top, not a prerequisite for the capstone.

| Section | Lessons | What you'll be able to do |
|:------|---------|---------------------------|
| **0 — Foundations: server + the workflow class** | 01, 02 | Bring up your own Postgres-backed Temporal stack via docker-compose. Recognize the building blocks (workflow, activity, worker, task queue, signal, query) and learn *why a workflow is a class* — state on `self`, `@workflow.signal`, `@workflow.query`, `wait_condition` — all in plain Temporal, no agent yet. |
| **1 — Your first durable agent** | 03, 04 | Run a Pydantic AI agent inside a Temporal workflow. See exactly which calls become **activities** (durable, retryable) vs which stay in the **workflow** (deterministic orchestration). |
| **2 — Configuration & resilience** | 05, 06 | Tune `ActivityConfig` — timeouts, retry policies, per-tool overrides. Stream model + tool events out of a workflow with `event_stream_handler`. |
| **3 — Long pauses & long work** | 07, 08 | Pause workflows for human approval (signals + `workflow.wait_condition`). Heartbeat long-running activities so the cluster knows they're alive. |
| **4 — Production polish (optional)** | 09 | Wire `LogfirePlugin` to correlate Temporal workflow history with span-level traces. Skippable without a Logfire account. |
| **5 — Capstone** | 10, 11 | A multi-agent research workflow (clarifier → researcher → writer) with HITL approval. Then put a FastAPI front-end on it — the langgraph-api analogue you already know. |

## How to study each lesson

Each lesson pairs a one-pager (`lessons/NN-*.md`) with a **directory** under
`examples/NN_<slug>/` containing at minimum:

- `worker.py` — the worker process that registers the workflow + activities
- `example.py` (or `starter.py`) — the client that kicks off a workflow

> **Aside — why directories, not single files?** Track 01 used one `.py` per
> lesson. Track 02 uses a directory per lesson because a Temporal app needs a
> worker *and* a starter — two files minimum — by convention.

The workflow:

1. **Read top to bottom: Review → Goal → TL;DR.** Each lesson opens by recalling
   the previous lesson (**Review**), stating where you're headed (**Goal**), and
   summarizing the mechanic in prose (**TL;DR**). Read all three on a first pass.
   The `## Pattern` block at the *bottom* is the cookbook — the canonical code
   for a months-later re-read ("remind me, how does HITL wire up again?").
   **Skip Pattern on a first read**; it gives away the shape before you've built
   the mental model.
2. **Bring up the server** if not already running: `make temporal-up`. Verify
   with `make temporal-status` — should say `SERVING`. Open `http://localhost:8080`.
3. **Start the worker** in terminal A: `make temporal-NN-worker`. Leave it
   running — Ctrl-C kills it.
4. **Run the starter** in terminal B: `make temporal-NN`. Watch the worker
   logs in terminal A.
5. **Open the Temporal UI** at `http://localhost:8080` and click into the
   workflow that just ran. Inspect the history. **This is where the lightbulb
   moments happen** — you literally see which calls were durable.
6. **Modify** — every lesson has at least one "Try it" idea. Tweak something.
   Restart the worker. Run again.
7. **Move on** when the "Bridge" section says what's next.

## Prerequisites

- Done Track 01 lessons 02-09 (you know `Agent`, tools, deps, capabilities).
- `docker` and `docker compose` working (`docker compose version` returns).
- `temporal` CLI on PATH — installed by `brew install temporal` (verify with
  `temporal --version`).
- `.env` with `GOOGLE_API_KEY` (lesson 03 onwards — lesson 02 is plain Temporal
  and needs no model) and `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` for the capstone.
- (Optional) A Logfire account for Lesson 09 — free tier is fine.

## The two-terminal pattern

You'll be in two terminals constantly for this track. Make your peace with it:

| Terminal A (worker) | Terminal B (starter / CLI) |
|---|---|
| `make temporal-02-worker` | `make temporal-02` |
| Hot-reload by Ctrl-C → re-run | Re-run as often as you like |
| Shows what the worker is doing | Shows what the starter is doing |

A real deployment runs the worker as a long-lived process (systemd, Docker,
k8s). For learning, your shell is the process manager.

## Coming from LangGraph / langgraph-api?

The mental-model translation lives in
[lesson 03 — Hello durable agent](./03-hello-durable.md) — it has the
authoritative table. Short version:

- A Temporal `workflow` is a langgraph graph compiled with a checkpointer
  that gives you hard determinism + retries + signals for free.
- A Temporal `activity` is a graph node whose result is memoized to durable
  storage; pydantic-ai automatically lifts model calls and tool calls into
  activities for you.
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

Start with [Lesson 01 — Temporal in 15 minutes](./01-temporal-tour.md).
