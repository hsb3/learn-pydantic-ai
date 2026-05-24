"""Capstone clarifier agent — narrows a vague topic into a researchable question.

Demonstrates **Lesson 05** in the capstone: `activity_config` sets the
base retry policy for every activity this agent generates (the model
request itself). Three attempts with exponential backoff; `UserError` /
`PydanticUserError` are auto non-retryable, and we add `ValueError` to
the list for input validation that should fail fast.
"""

from __future__ import annotations

from datetime import timedelta

from pydantic_ai import Agent
from pydantic_ai.durable_exec.temporal import TemporalAgent
from temporalio.common import RetryPolicy

from learn_pydantic_ai import FLASH

_base = Agent(
    model=FLASH,
    name="capstone_clarifier",
    instructions=(
        "Given a topic and some pre-fetched context, return ONE focused "
        "researchable question. Keep it under 20 words."
    ),
)

# Lesson 05 — base `activity_config` applies to every activity from this agent.
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
