"""10 — Multi-agent delegation.

The simplest multi-agent pattern: one agent's tool calls another agent and
returns the inner result. The parent stays in charge; the child is a
specialist.

Why split agents instead of giving the parent more tools?
- Each agent gets a focused system prompt and (optionally) a different model
- The child can have its own structured output type
- The parent doesn't see the child's intermediate tool calls — only the
  distilled answer

Pass `usage=ctx.usage` when delegating so the parent's token-usage totals
include the child's calls.
"""

from __future__ import annotations

import asyncio

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from _common import FLASH


class Outline(BaseModel):
    title: str
    bullets: list[str]


# ── Child: produces a structured outline ───────────────────────────────────
outliner = Agent(
    FLASH,
    output_type=Outline,
    instructions=(
        "Produce a tight outline: catchy title, 3-5 bullet points. "
        "Bullets are short noun phrases, no full sentences."
    ),
)

# ── Parent: writes prose, delegating outline planning to the child ─────────
writer = Agent(
    FLASH,
    instructions=(
        "You write punchy short blog posts (3 paragraphs). "
        "Before writing, call `make_outline` to plan the structure, then "
        "write the post following the outline."
    ),
)


@writer.tool
async def make_outline(ctx: RunContext[None], topic: str) -> Outline:
    """Plan an outline for the given topic. Returns title + bullet points."""
    # Threading `usage=ctx.usage` rolls the child's token usage into the parent.
    result = await outliner.run(topic, usage=ctx.usage)
    return result.output


async def main() -> None:
    result = await writer.run("Why uv is replacing pip for new Python projects")
    print(result.output)
    print("---")
    # Combined usage from both agents:
    print(result.usage)


if __name__ == "__main__":
    asyncio.run(main())
