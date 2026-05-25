"""Lesson 05 — tune retries and timeouts via `ActivityConfig`.

Every model call and every tool call that pydantic-ai lifts into a Temporal
activity inherits an `ActivityConfig`. By default it's just
`start_to_close_timeout=60s` and the framework-default `RetryPolicy`. You
override it in three layered places on `TemporalAgent`:

- `activity_config=` — base for everything the agent does (model + tools)
- `model_activity_config=` — model-call activities only
- `tool_activity_config={toolset_id: {tool_name: ActivityConfig | False}}` —
  per-tool override (False disables the activity wrap entirely)

`ActivityConfig` is a TypedDict, not a class; pass a plain dict literal.

A tool that's added via `@agent.tool_plain` / `@agent.tool` lives in the
agent's built-in function toolset whose id is the literal string `'<agent>'` —
that's the key to use in `tool_activity_config`.

The agent here owns a single flaky tool that's wired to retry up to 5 times
with short backoff so a single workflow run takes seconds, not minutes.
"""

from __future__ import annotations

from datetime import timedelta

from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import PydanticAIWorkflow, TemporalAgent
from temporalio import workflow
from temporalio.common import RetryPolicy

from learn_pydantic_ai import FLASH
from flaky_tool import flaky_lookup

_base = Agent(
    model=FLASH,
    name="lookup_agent",
    instructions=(
        "You answer questions by calling the `flaky_lookup` tool exactly once "
        "with a relevant query string, then summarising the result for the user. "
        "Do not retry the tool yourself — the framework will."
    ),
)
_base.tool_plain(flaky_lookup)

# This is the per-tool retry policy you'll watch in the Temporal UI. Maximum
# 5 attempts is enough to ride out FAIL_FIRST_N = 2 plus a small buffer.
# 200ms initial interval keeps the demo snappy. `non_retryable_error_types`
# lets you mark exceptions that should fail fast instead of retrying — handy
# for "this input will never work, don't waste time".
_flaky_tool_retry = RetryPolicy(
    initial_interval=timedelta(milliseconds=200),
    backoff_coefficient=2.0,
    maximum_attempts=5,
    non_retryable_error_types=["ValueError"],
)

lookup_agent = TemporalAgent(
    _base,
    # Defaults applied to model + tool activities unless a more specific config
    # overrides. 30s here is well over what the demo needs.
    activity_config={"start_to_close_timeout": timedelta(seconds=30)},
    # Model calls get a longer timeout because LLM responses can be slow.
    model_activity_config={"start_to_close_timeout": timedelta(seconds=60)},
    # Per-tool override. Toolset id `'<agent>'` is the agent's built-in
    # function toolset where `@agent.tool*` registers go.
    tool_activity_config={
        "<agent>": {
            "flaky_lookup": {
                "start_to_close_timeout": timedelta(seconds=10),
                "retry_policy": _flaky_tool_retry,
            },
        },
    },
)


@workflow.defn
class LookupWorkflow(PydanticAIWorkflow):
    """Run the agent. Tool retries happen invisibly from the workflow's POV."""

    __pydantic_ai_agents__ = [lookup_agent]

    @workflow.run
    async def run(self, prompt: str) -> str:
        workflow.logger.info("LookupWorkflow.run prompt=%r", prompt)
        result = await lookup_agent.run(prompt)
        return result.output
