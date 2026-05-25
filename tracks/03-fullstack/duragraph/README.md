# duragraph

A **langgraph-api-shaped run/thread server** on **Temporal + Pydantic AI**. It recreates the part of LangGraph Platform you actually use — threads, runs, streaming, state, human-in-the-loop — without the proprietary coupling, and with the full Temporal Web UI for debugging every run.

## The one structural bet

Everything falls out of a single decision: **a thread is a long-lived Temporal workflow.**

| langgraph-api concept | duragraph endpoint | Temporal mechanism |
|---|---|---|
| Create thread | `POST /threads` | `start_workflow("ThreadWorkflow", id=thread_id)` |
| Start run (background) | `POST /threads/{id}/runs` | `submit_run` **signal** |
| Start run (stream) | `POST /threads/{id}/runs/stream` | subscribe Redis → `submit_run` signal → SSE |
| Get thread state | `GET /threads/{id}/state` | `get_state` **query** |
| Get history | `GET /threads/{id}/history` | `get_history` **query** |
| Run status | `GET /threads/{id}/runs/{run_id}` | `get_run_status` **query** |
| Cancel run | `POST /threads/{id}/runs/{run_id}/cancel` | `cancel_run` **signal** |
| Resume interrupt (HITL) | `POST /threads/{id}/runs` with `command.resume` | `resume` **signal** |
| Assistant (graph+config) | `POST/GET /assistants` | registry row → Pydantic AI agent key |
| Checkpointing / retries / crash recovery | (free) | Temporal event history |

The durable agent loop itself is **not yours to write**: `TemporalAgent(agent)` turns a normal Pydantic AI agent into a workflow component where every model/tool/MCP call is an automatic, retryable activity.

## Layout

```
app/                      # the API (never imports the agent/model stack)
  routes/                 # threads.py, runs.py, assistants.py  -> the contract
  services/
    temporal_gateway.py   # brain: maps ops to Temporal client calls (by string name)
    streaming.py          # Redis pub/sub -> SSE subscriber
  schemas.py  core/  deps.py  main.py
worker/                   # the durable core (the only place agents live)
  agents.py               # Pydantic AI agents wrapped as TemporalAgent + stream seam
  workflows.py            # ThreadWorkflow (actor: signals=runs, queries=state, HITL)
  activities.py client.py worker.py streaming_publish.py
```

## Run it locally

```bash
docker compose up -d temporal temporal-ui redis     # Temporal :7233, UI :8233, Redis :6379
pip install -e .                                    # or: uv sync
export OPENAI_API_KEY=...                            # whichever provider your agent uses
python -m worker.worker                              # terminal 1: the durable core
uvicorn app.main:app --reload                        # terminal 2: the API
```

Smoke test the contract:

```bash
TID=$(curl -s localhost:8000/threads -d '{}' -H 'content-type: application/json' | jq -r .thread_id)
curl -N localhost:8000/threads/$TID/runs/stream -H 'content-type: application/json' \
  -d '{"assistant_id":"asst_chat","input":{"messages":[{"role":"user","content":"hi"}]},"stream_mode":["messages"]}'
curl -s localhost:8000/threads/$TID/state | jq      # durable state, queried from the workflow
```

Run the streaming-handler test any time:

```bash
OPENAI_API_KEY=sk-test python -m pytest tests/
```

Open the Temporal Web UI at `http://localhost:8233` and watch the event history of the thread workflow — this is the debugging visibility langgraph-api hid from you.

## Rejection map (the one error envelope)

All errors return `{code, message, detail?}`. `code` is stable contract.

| code | HTTP | raised when |
|---|---|---|
| `thread_not_found` | 404 | thread workflow missing / not running |
| `run_not_found` | 404 | unknown run_id on thread, or resume with no interrupt |
| `assistant_not_found` | 404 | unknown assistant_id |
| `run_not_interrupted` | 409 | resume on a run that isn't waiting |
| `worker_unavailable` | 503 | query timed out — worker fleet down |

## What's done vs. what's genuinely yours

**Done (the hard, proprietary parts):** thread/run lifecycle, durable state, query-based state/history, signal-based runs + cancel + HITL resume, the Redis→SSE plumbing end-to-end, error envelope, layered structure, local + compose stack.

**Your remaining work — in priority order (resist scope creep on the rest):**
1. ~~Token-stream mapping~~ **DONE** — `worker/agents.py:event_stream_handler` maps pydantic-ai stream events to `messages`/`updates`/`events`, verified against pydantic-ai 1.102.0 by `tests/test_event_stream_handler.py`. Re-run that test after any pydantic-ai upgrade (it's the version-drift guard). What remains: wire your real provider key and confirm the live token stream end-to-end.
2. **Auth** — one dependency in `app/main.py`: validate your JWT (the authorizer you'd use to drop NGINX) and inject tenant/user context.
3. **Persistence of metadata** — swap the in-memory assistant store + thread metadata for Supabase. Durable *run* state already lives in Temporal; this is just the catalog.
4. **Message-history threading** — the scaffold stringifies the conversation (as the Pydantic AI example does); thread real `ModelMessage` history and externalize large state to stay under Temporal's 2MB payload ceiling.
5. **Resumable streams** (only if you need refresh-mid-response / multi-device) — upgrade Redis pub/sub to Redis Streams + `Last-Event-ID`.

## Borrowed from

- `pydantic/pydantic-ai-temporal-example` — `TemporalAgent`/`AgentPlugin`/`PydanticAIPlugin` wiring; the thread-actor `wait_condition` loop.
- `steveandroulakis/temporal-ai-agent` — start-or-signal pattern, query-for-state, signal-based HITL.
- architectingbytes.com — Temporal worker → Redis → SSE streaming.
