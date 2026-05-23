# Runtimes — identity + durability

*Appendix, outside the numbered curriculum.* Read this once you've worked through Lessons 02-12 and want to host an agent or make it crash-safe.

> **Your framing:** a runtime = identity (the agent is reachable as a distinct thing) + durability (its state survives). Pydantic-AI gives you each as a separate, swappable layer. Pick à la carte.

## 1. Identity — turn an agent into a thing you can talk to

The agent loop is just a Python object by default. To give it identity, pydantic-ai ships **`to_X()` factory methods** that adapt an `Agent` into a runnable application of various shapes. Same agent, multiple frontages.

| Method | Returns | What it gives you | Serve with |
|---|---|---|---|
| `agent.to_cli()` / `to_cli_sync()` | *(runs)* | Interactive terminal REPL bound to **this specific agent** | direct call |
| `agent.to_web()` | `Starlette` app | A hosted chat UI for this agent (HTML + SSE streaming) | `uvicorn` |
| `agent.to_a2a()` | `FastA2A` app | ASGI app speaking the [Agent-to-Agent](https://google.github.io/A2A/) protocol | `uvicorn` |
| `agent.to_ag_ui()` | `AGUIApp` | ASGI app speaking the AG-UI wire format (chat UIs, streaming) | `uvicorn` |

### `clai` — the global REPL / one-shot CLI

`clai` is the bundled CLI. It's installed as `pai` by the `pydantic-ai` package (use `uv run pai …`) and as `clai` by the standalone `clai` PyPI wrapper. Identical program either way; the internal `prog_name` is `clai` regardless.

```bash
# One-shot prompt with a default model
uv run pai "Summarise the difference between A2A and AG-UI in two lines."

# Interactive REPL (rich, with /commands, slash-help, multi-line, history)
uv run pai

# REPL bound to YOUR agent (lesson 12 YAML spec — could be a Python "module:variable" too)
uv run pai --agent tracks/01-intro/examples/agent.yaml

# clai's web subcommand — hosts ANY agent (default, file, or module:var) at a chat UI
uv run pai web --agent tracks/01-intro/examples/agent.yaml --port 8001
# open http://localhost:8001
```

If you want the `clai` name specifically: `uv add --dev clai` then `uv run clai …`.

### `Agent.to_web()` — your agent + your fastapi/uvicorn stack

```python
# server.py
import uvicorn
from pydantic_ai import Agent

agent = Agent("google:gemini-3-flash-preview", instructions="Be concise.")
app = agent.to_web()   # -> starlette.Starlette
# app is a normal ASGI app — mount under /, add middleware, etc.

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

Same idea for `to_a2a()` (Agent-to-Agent protocol — interop with other A2A agents) and `to_ag_ui()` (AG-UI streaming protocol — plug into front-ends that speak it).

### Which adapter for which situation?

| You want… | Reach for |
|---|---|
| Test an agent at a terminal, with REPL | `clai` / `pai`, or `agent.to_cli()` |
| A chat UI without writing a frontend | `clai web` or `agent.to_web()` |
| Other agents to call yours over HTTP | `agent.to_a2a()` |
| Plug into a custom React/Next.js front-end | `agent.to_ag_ui()` |
| Anything serious | uvicorn + one of `to_web` / `to_a2a` / `to_ag_ui` |

---

## 2. Durability — agents that survive crashes (Temporal teaser)

**The problem.** A long-running agent run — tool calls that take minutes, human approvals that take days, retries that need exponential backoff — should not die when the worker process restarts. The default in-process loop has no persistence layer; if the Python process dies mid-run, the state is gone.

**The solution.** Pydantic-AI ships first-class adapters into three durable workflow runtimes:

| Runtime | Module | When to pick it |
|---|---|---|
| **Temporal** | `pydantic_ai.durable_exec.temporal` | Most mature ecosystem; battle-tested at huge scale; Temporal Cloud or self-host |
| **DBOS** | `pydantic_ai.durable_exec.dbos` | Postgres-native durability; simpler ops if you already run Postgres |
| **Prefect** | `pydantic_ai.durable_exec.prefect` | Best fit if you already use Prefect for data pipelines |

Same architectural shape across all three: wrap the agent in a workflow class, register a plugin with the worker, run.

### The Temporal trio

```python
from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import (
    TemporalAgent,        # wraps your Agent — same API, durable execution
    PydanticAIWorkflow,   # base class your @workflow.defn extends
    PydanticAIPlugin,     # tells the Temporal worker how to handle PydanticAI activities
)
```

- **`TemporalAgent(wrapped_agent)`** — Adapter that wraps a normal `Agent` and routes its model calls, tool calls, and toolsets through Temporal activities. The activities are checkpointed; if the worker dies mid-tool-call, Temporal replays the workflow from the last checkpoint without re-calling the (potentially expensive) tools.
- **`PydanticAIWorkflow`** — Base class for `@workflow.defn`-decorated workflow classes. Knows how to call into a `TemporalAgent` safely from inside a workflow context.
- **`PydanticAIPlugin`** — Registered on your Temporal worker; teaches it about pydantic-ai-specific activity types, serialization, and the LogfirePlugin if you're using it.

### Mental model

In Temporal world there are two kinds of code:

| Code kind | Property | Pydantic-AI plays this role |
|---|---|---|
| **Workflow** | Deterministic, replayable. No side effects. Drives the orchestration. | Your `PydanticAIWorkflow` subclass; `TemporalAgent.run(...)` calls inside it |
| **Activity** | Non-deterministic, side-effecting. Retriable. Lives outside the workflow's deterministic replay. | Model calls + your tool functions — pydantic-ai wraps each one as an activity automatically |

The win: you write what looks like ordinary `agent.run(prompt)` code. Behind the scenes every model call and tool call becomes a durable activity. Server restart? The workflow resumes from the last checkpointed activity result, no replays of completed work.

### Sketch (not runnable as-is — assumes a worker is up)

```python
from temporalio import workflow
from temporalio.client import Client
from temporalio.worker import Worker

from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import (
    TemporalAgent, PydanticAIWorkflow, PydanticAIPlugin,
)

base = Agent("google:gemini-3-flash-preview", instructions="…")
durable = TemporalAgent(base, name="research-agent")


@workflow.defn
class ResearchWorkflow(PydanticAIWorkflow):
    @workflow.run
    async def run(self, topic: str) -> str:
        result = await durable.run(f"Research: {topic}")
        return result.output


async def main():
    client = await Client.connect("localhost:7233", plugins=[PydanticAIPlugin()])
    async with Worker(
        client, task_queue="research-q",
        workflows=[ResearchWorkflow], activities=durable.activities,
        plugins=[PydanticAIPlugin()],
    ):
        out = await client.execute_workflow(
            ResearchWorkflow.run, "agent runtimes",
            id="research-1", task_queue="research-q",
        )
        print(out)
```

### What you'd need to actually run this

1. A Temporal cluster — `temporal server start-dev` for local, or Temporal Cloud
2. The `temporalio` Python SDK in your deps
3. A long-running worker process (the `async with Worker(...)` block above)
4. A starter — any client that calls `execute_workflow(...)` (CLI script, FastAPI endpoint, scheduled job)

### Why this matters for "runtime = identity + durability"

- **Identity** = `name="research-agent"` on `TemporalAgent` + the workflow id. Other systems route to it via the Temporal task queue.
- **Durability** = the workflow + activity replay model. Crash mid-run → resume from last activity. Tool times out → automatic exponential-backoff retry. Human-in-the-loop pause → workflow sleeps for days; resumes when signalled.

### Deep dive — coming later

Topics worth a dedicated lesson when you're ready:
- `TemporalAgent` lifecycle: which methods become activities, which stay in the workflow
- `activity_config` / `model_activity_config` — per-activity retry policy, heartbeats, timeouts
- `event_stream_handler` for streaming tokens out of a Temporal workflow to a UI
- `TemporalRunContext` — what changes about `RunContext` inside a workflow
- Patterns: human approval via `workflow.wait_condition`, long-running tools as separate activities, signals for cancel/pause
- Self-hosted vs Temporal Cloud, observability with Logfire's `LogfirePlugin`

---

## TL;DR

- **Identity:** `clai` (terminal), `agent.to_cli()`, `agent.to_web()` (Starlette + uvicorn), `agent.to_a2a()`, `agent.to_ag_ui()`. Pick the protocol that matches who's calling.
- **Durability:** wrap with `TemporalAgent`, run inside a `PydanticAIWorkflow`, register `PydanticAIPlugin` on the worker. Same agent code, durable everywhere.
- DBOS and Prefect are drop-in alternatives if Temporal isn't your team's choice.
