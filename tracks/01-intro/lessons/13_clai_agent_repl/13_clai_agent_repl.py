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
# ---

# %%
"""Lesson 13 companion — stub notebook for the project-local clai agent.

Open in VS Code (cells via `# %%`) or `jupyter lab`. This is intentionally
short: it introduces the agent defined in `cli_agent.yaml` and
then hands off to the Makefile shortcuts for the actual REPL workflow.
"""

# %% [markdown]
# # Lesson 13 — project-local `clai` agent (stub)
#
# Read [`lessons/13-clai-agent-repl.md`](../lessons/13-clai-agent-repl.md)
# alongside this notebook. The point of Lesson 13 is *combining* — there's
# no new pydantic-ai API. We're plugging the YAML pattern from Lesson 12
# into the bundled `clai` REPL.

# %% [markdown]
# ## 1. Inspect the spec
#
# The agent lives in `cli_agent.yaml`. Read it once; the values
# here drive the REPL's behavior.

# %%
from pathlib import Path

spec = Path("cli_agent.yaml").read_text()
print(spec)

# %% [markdown]
# ## 2. Load it the same way `clai` does
#
# Under the hood, `pai --agent cli_agent.yaml` calls
# `Agent.from_file()`. You can do the exact same thing in Python:

# %%
from dotenv import load_dotenv

load_dotenv()

from pydantic_ai import Agent

agent = Agent.from_file("cli_agent.yaml")
agent

# %%
# Quick sanity check — confirm the agent loaded with the YAML's settings.
print("model:", agent.model)
print("output_type:", agent.output_type)

# %% [markdown]
# ## 3. Use it
#
# Three ways, ordered by ergonomics for daily use:
#
# 1. **`make repl`** — interactive REPL. This is the intended workflow.
# 2. **`make repl-prompt P="your question"`** — one-shot from your shell.
# 3. **Programmatic** — what this notebook is doing. Useful when you want
#    a tested Python entry point rather than a terminal session.

# %%
# Programmatic one-shot (the equivalent of `make repl-prompt P="..."`).
result = await agent.run("In one line, what is pydantic-ai's `clai` for?")
print(result.output)

# %% [markdown]
# ## 4. From here
#
# - For interactive use, exit this notebook and run `make repl`.
# - For hosting beyond the terminal — `Agent.to_web()`, `Agent.to_a2a()`,
#   durable execution with Temporal — see [`lessons/runtimes.md`](../lessons/runtimes.md).
