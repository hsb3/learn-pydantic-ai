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
"""Lesson 01 companion — runnable tour of the Agent API.

Open in VS Code (Python extension recognises `# %%` cells) or convert to
.ipynb with `uv run --with jupytext jupytext --to ipynb 01_agent_api_tour.py`.

Notebook uses `await agent.run(...)` instead of `agent.run_sync(...)`.
`run_sync` doesn't work inside Jupyter/VS Code's running event loop —
top-level `await` is the canonical interactive pattern anyway. The other
examples (02-12) use `run_sync` because they're scripts.
"""

# %% [markdown]
# # Lesson 01 — Agent API tour (runnable)
#
# Read [`lessons/01-agent-api-tour.md`](../lessons/01-agent-api-tour.md) alongside this notebook.
# Each section below corresponds to one section of the tour. Run a cell,
# look at the output, change something, run it again.

# %%
from learn_pydantic_ai import FLASH

# %% [markdown]
# ## 1. The Agent constructor
#
# The simplest possible agent: model + instructions.

# %%
from pydantic_ai import Agent

agent: Agent[None, str] = Agent(
    model=FLASH, name="agent-01", instructions="Reply in one short sentence."
)

agent

# %%
# Inspect a few public attributes. Don't mutate these — pretend they're read-only.
print("model:", agent.model)
print("name:", agent.name)
print("deps_type:", agent.deps_type)
print("output_type:", agent.output_type)

# %%
# Look at the public surface (filter dunder + private).
public = sorted(a for a in dir(agent) if not a.startswith("_"))
print(public)

# %% [markdown]
# ## 2. Run methods
#
# Same agent, different ways to call it. In a notebook we use `await
# agent.run(...)` — the sync `run_sync` calls `asyncio.run()` internally
# and clashes with Jupyter's already-running event loop.

# %%
from pydantic_ai.run import AgentRunResult

result: AgentRunResult[str] = await agent.run(user_prompt="What is 2 + 2?")
print(result.output)

# %%
# Same answer via the async API. In a script you'd write `agent.run_sync(...)`.
result: AgentRunResult[str] = await agent.run(user_prompt="Name a small mammal.")
print(result.output)

# %% [markdown]
# **Try it:** change `instructions=` on the agent above (re-run the
# constructor cell, then this one). Watch how the system prompt steers
# the answer.

# %%
# run_stream — async context manager, tokens arrive as they're produced
import sys

async with agent.run_stream("Describe the color cobalt in one sentence.") as stream:
    async for delta in stream.stream_text(delta=True):
        sys.stdout.write(delta)
        sys.stdout.flush()
    print()
    print("---usage:", stream.usage)

# %% [markdown]
# ## 3. The RunResult object

# %%
result = await agent.run("Pick a number between 1 and 10.")

# .output: typed result (str here because no output_type was set)
print("output:", repr(result.output))

# .usage: token counts (Gemini's thoughts_tokens is internal reasoning)
print("usage:", result.usage)

# %%
# .all_messages() — the full transcript. .new_messages() is just this run's part.
for msg in result.all_messages():
    parts_summary = [type(p).__name__ for p in msg.parts]
    print(f"{type(msg).__name__:15} parts={parts_summary}")

# %% [markdown]
# ## 4. Decorators that register behavior
#
# Tools let the model call your Python. `@agent.tool_plain` is the simplest form.

# %%
# Build a fresh agent so we can attach tools.
import random

dice_agent: Agent[None, str] = Agent(
    model=FLASH,
    name="dice-agent",
    instructions="When asked to gamble, roll the die using your tool.",
)


@dice_agent.tool_plain
def roll_dice() -> int:
    """Roll a fair six-sided die. Returns 1-6."""
    return random.randint(1, 6)


result: AgentRunResult[str] = await dice_agent.run(user_prompt="Roll me a die.")
print(result.output)

# %%
# number of times to roll the die
num_rolls: int = 2
times_rolled = 0
result_total = 0

for _ in range(num_rolls):
    result_total += roll_dice()
    times_rolled += 1

if times_rolled > 0:
    avg_roll = result_total / times_rolled
    print(f"Rolled the die {times_rolled} times. Average roll: {avg_roll:.2f}")

# %%
# Inspect the loop — request → tool call → tool return → text
for msg in result.all_messages():
    for part in msg.parts:
        label = type(part).__name__
        if label == "UserPromptPart":
            print(f"{label:18} {part.content!r}")
        elif label == "ToolCallPart":
            print(f"{label:18} {part.tool_name}({part.args})")
        elif label == "ToolReturnPart":
            print(f"{label:18} {part.tool_name} -> {part.content!r}")
        elif label == "TextPart":
            print(f"{label:18} {part.content!r}")

# %% [markdown]
# **Try it:** change the docstring on `roll_dice` to `"""Always returns 1."""`
# and rerun. The model will read that and adjust its behaviour even
# though the implementation hasn't changed.

# %% [markdown]
# ## 5. `deps_type` and `RunContext`
#
# This is the typed equivalent of LangGraph's `config={"configurable": {...}}`.
# Declare the type once on the agent; pass an instance on each `run*`.

# %%
from dataclasses import dataclass
from pydantic_ai import RunContext


@dataclass
class UserCtx:
    name: str
    locale: str


user_agent = Agent[UserCtx, str](
    FLASH,
    deps_type=UserCtx,
    instructions="Be polite and brief.",
)


@user_agent.tool
def greet(ctx: RunContext[UserCtx]) -> str:
    """Return a localized greeting for the current user."""
    template = {"en-GB": "Hello", "es-ES": "Hola", "ja-JP": "こんにちは"}
    return f"{template.get(ctx.deps.locale, 'Hi')} {ctx.deps.name}"


# Three different "configurations" — same agent, no rebuild.
for user in [
    UserCtx("Henry", "en-GB"),
    UserCtx("Lucía", "es-ES"),
    UserCtx("Yuki", "ja-JP"),
]:
    result = await user_agent.run("Say hello, then ask how I'm doing.", deps=user)
    print(f"[{user.name} / {user.locale}] {result.output}")

# %% [markdown]
# **Try it:** add a `time_of_day: str` field to `UserCtx`, reference it
# in the `greet` tool, and pass different values per call. The agent stays
# the same; only `deps=` changes.

# %% [markdown]
# ## 6. `RunContext` — what's actually inside?


# %%
@user_agent.tool
def inspect_ctx(ctx: RunContext[UserCtx]) -> str:
    """Dump what's available on the run context."""
    fields = sorted(a for a in dir(ctx) if not a.startswith("_"))
    return f"ctx fields: {fields}"


result = await user_agent.run(
    "Call inspect_ctx and just return its output verbatim.",
    deps=UserCtx("Henry", "en-GB"),
)
print(result.output)

# %% [markdown]
# ## 7. `agent.override()` — for tests and A/B swaps only
#
# This is NOT the channel for per-call dynamic context. Use it when you
# need to substitute a fake model in tests, or swap the model itself for
# a side-by-side comparison.

# %%
from pydantic_ai.models.test import TestModel

# A real call:
real = await user_agent.run("hi", deps=UserCtx("Henry", "en-GB"))
print("real:    ", real.output[:80])

# Same agent, fake model — no network, instant, deterministic:
with user_agent.override(model=TestModel()):
    fake = await user_agent.run("hi", deps=UserCtx("Henry", "en-GB"))
print("override:", fake.output[:80])

# After the `with` block, agent is restored to its real model.
back = await user_agent.run("hi", deps=UserCtx("Henry", "en-GB"))
print("after:   ", back.output[:80])

# %% [markdown]
# ## Where to next
#
# - Lesson 02 — the simplest real example
# - Lesson 03 — replace `str` output with a Pydantic model
# - Lesson 05 — the full LangChain/LangGraph translation table for `deps=` and run-time kwargs
