"""Lesson 03 — the smallest pydantic-ai agent wrapped in a Temporal workflow.

The pattern every later lesson reuses:

1. Build a regular `Agent` at module scope. `name=` is required — Temporal
   uses it to derive deterministic activity names.
2. Wrap it in `TemporalAgent`. That re-points the agent's model + tool calls
   at Temporal activities (durable, retryable) without changing the call
   site inside the workflow.
3. Define a `@workflow.defn` class inheriting `PydanticAIWorkflow` and list
   the agents in `__pydantic_ai_agents__`. The `PydanticAIPlugin` discovers
   those agents at worker-startup time and registers their activities.

The `await hello_agent.run(prompt)` line inside the workflow looks
identical to the synchronous `Agent.run()` from Track 01 — but every model
call it makes is now scheduled as a Temporal activity behind the scenes.
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import PydanticAIWorkflow, TemporalAgent
from temporalio import workflow

from learn_pydantic_ai import FLASH

# CRITICAL: `name=` is required on every Agent wrapped by TemporalAgent.
# Temporal derives activity names from it (e.g. `hello_durable__model_request`).
_base = Agent(
    model=FLASH,
    name="hello_durable",
    instructions="Reply in one short sentence.",
)
hello_agent = TemporalAgent(_base)


@workflow.defn
class HelloWorkflow(PydanticAIWorkflow):
    """The simplest durable agent — one prompt in, one string out."""

    # PydanticAIPlugin walks this list at worker startup and registers each
    # agent's auto-generated activities. No manual `activities=[...]` needed.
    __pydantic_ai_agents__ = [hello_agent]

    @workflow.run
    async def run(self, prompt: str) -> str:
        # Looks like a plain agent call. Under the hood: the model request
        # is scheduled as an activity, results are memoized in workflow
        # history, and a crash mid-call is retried automatically.
        result = await hello_agent.run(prompt)
        return result.output
