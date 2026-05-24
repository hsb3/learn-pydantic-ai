# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.3
#   kernelspec:
#     display_name: learn-pydantic-ai (3.13.13)
#     language: python
#     name: python3
# ---

# %%
"""Lesson 01 companion — runnable Temporal tour.

This notebook bootstraps an in-process Temporal server via
`WorkflowEnvironment.start_local()` so you can poke the primitives without
needing the docker stack up. The "real" workflow for every later lesson runs
against `make temporal-up` instead.

Read `lessons/01-temporal-tour.md` alongside.
"""

# %% [markdown]
# # Lesson 01 — Temporal in 15 minutes
#
# Four primitives: **workflow**, **activity**, **worker**, **task queue**.
# This notebook touches every one.

# %%
from datetime import timedelta

# Standard temporalio imports we'll use throughout the track.
from temporalio import activity, workflow
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import UnsandboxedWorkflowRunner, Worker

# %% [markdown]
# ## 1. Define an activity
#
# Activities are where side effects live: HTTP calls, file I/O, model
# inference. The decorator marks the function as something a workflow is
# allowed to invoke through Temporal (instead of calling directly).


# %%
@activity.defn
async def say_hello(name: str) -> str:
    """Side-effecting function. Could call an API; here it just returns a string."""
    return f"Hello, {name}!"


# %% [markdown]
# ## 2. Define a workflow
#
# Workflow code is **deterministic** — no `random`, no `datetime.now()`, no
# `httpx.get()`. Anything non-deterministic goes in an activity, which the
# workflow calls via `workflow.execute_activity(...)`. The activity result
# is memoized in workflow history so replay reproduces the same state.


# %%
@workflow.defn
class GreetWorkflow:
    """The simplest possible Temporal workflow — one activity call."""

    @workflow.run
    async def run(self, name: str) -> str:
        return await workflow.execute_activity(
            say_hello,
            name,
            start_to_close_timeout=timedelta(seconds=10),
        )


# %% [markdown]
# ## 3. Start an ephemeral server + worker
#
# `WorkflowEnvironment.start_local()` spins up a real Temporal server in a
# subprocess and tears it down when the `async with` exits. Use it for
# notebooks and tests; use the docker stack (`make temporal-up`) for "real"
# multi-terminal lessons.


# %%
async def run_demo() -> str:
    async with await WorkflowEnvironment.start_local() as env:
        # The worker polls a task queue and runs whatever code it finds.
        # `UnsandboxedWorkflowRunner` is used here because Jupyter's `__main__`
        # module lacks a `__file__` attribute that the default sandbox needs.
        # In a regular .py file (every other lesson) you omit this and let the
        # sandbox enforce determinism for you.
        async with Worker(
            env.client,
            task_queue="lesson-01-tour",
            workflows=[GreetWorkflow],
            activities=[say_hello],
            workflow_runner=UnsandboxedWorkflowRunner(),
        ):
            # Start the workflow and await its result.
            result: str = await env.client.execute_workflow(
                GreetWorkflow.run,
                "Henry",
                id="lesson-01-greet",
                task_queue="lesson-01-tour",
            )
            return result


# %%
result = await run_demo()  # type: ignore[top-level-await]  # ok in Jupyter
print(result)

# %% [markdown]
# ## 4. What just happened?
#
# 1. The client called `execute_workflow(GreetWorkflow.run, "Henry", ...)`.
# 2. Temporal recorded `WorkflowExecutionStarted` in workflow history.
# 3. The worker picked up the workflow task, ran `GreetWorkflow.run` until
#    it hit `await workflow.execute_activity(say_hello, ...)`.
# 4. Temporal scheduled an activity task. The worker picked it up.
#    `say_hello` ran. The result was sent back, recorded as
#    `ActivityTaskCompleted`, and returned to the workflow.
# 5. The workflow returned. Temporal recorded `WorkflowExecutionCompleted`.
#
# If the worker had crashed at step 4, Temporal would re-schedule the
# activity. If it crashed during the workflow body, replay reconstructs
# state from history.

# %% [markdown]
# ## 5. (Optional) Connect to your docker stack instead
#
# Once `make temporal-up` is running, you can connect via
# `learn_pydantic_ai.connect()` and start the same workflow there. Then it
# shows up in the Temporal UI at <http://localhost:8080>.

# %%
# Uncomment to run against your local docker stack instead of the ephemeral env.
#
# from learn_pydantic_ai import connect, TASK_QUEUE
#
# client = await connect()
# async with Worker(
#     client,
#     task_queue="lesson-01-tour",  # any task queue name; clients/workers must agree
#     workflows=[GreetWorkflow],
#     activities=[say_hello],
# ):
#     result = await client.execute_workflow(
#         GreetWorkflow.run, "Henry",
#         id="lesson-01-greet-docker",
#         task_queue="lesson-01-tour",
#     )
#     print(result)

# %% [markdown]
# ## What's next
#
# Lesson 03 wraps a real pydantic-ai `Agent` in a workflow. The `say_hello`
# activity becomes an LLM call; the boilerplate stays the same.
