"""14 — Observability with Logfire.

Watch every agent call, tool call, model request, and HTTP round-trip show
up in Logfire's UI as a nested trace tree. Three lines of setup gives you
that picture for any pydantic-ai code you write.

The setup:

1. `logfire.configure(send_to_logfire="if-token-present")` — initialises the
   OpenTelemetry tracer. With `LOGFIRE_TOKEN` set, traces ship to
   https://logfire.pydantic.dev; without it, instrumentation still runs
   (spans are created locally) but the network exporter is a no-op. That's
   why this lesson works fine without a Logfire account.

2. `logfire.instrument_pydantic_ai()` — emits first-class spans for
   `Agent.run`, tool calls, model requests, and structured-output parsing.

3. `logfire.instrument_httpx(capture_all=True)` — bonus: see the actual
   HTTP POST to the model provider as a child span under each model
   request. Disable in production if request bodies are sensitive.

We then run a small multi-agent setup (parent `writer` delegating to child
`outliner`) so the trace tree shows meaningful nesting: parent agent →
tool call → child agent → model request → HTTP POST.
"""

from __future__ import annotations

import asyncio
import os

import logfire
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from learn_pydantic_ai import FLASH


def _configure_logfire() -> None:
    """Initialise Logfire. Call once at startup, never per-request."""
    logfire.configure(
        service_name="learn-pydantic-ai-lesson-14",
        send_to_logfire="if-token-present",
        scrubbing=False,
    )
    logfire.instrument_pydantic_ai()
    logfire.instrument_httpx(capture_all=True)
    if os.getenv("LOGFIRE_TOKEN"):
        print("Logfire enabled — open https://logfire.pydantic.dev to view traces.")
    else:
        print(
            "LOGFIRE_TOKEN not set — Logfire instrumentation is active but "
            "not transmitting. Set the token in .env to see this run in the UI."
        )


# ── Child: produces a structured outline ─────────────────────────────────────
class Outline(BaseModel):
    title: str
    bullets: list[str]


outliner = Agent(
    FLASH,
    output_type=Outline,
    instructions=(
        "Produce a tight outline: catchy title, 3-5 bullet points. "
        "Bullets are short noun phrases, no full sentences."
    ),
)


# ── Parent: writes prose, delegating outline planning to the child ───────────
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
    # `usage=ctx.usage` rolls the child's tokens into the parent's RunUsage.
    result = await outliner.run(topic, usage=ctx.usage)
    return result.output


async def main() -> None:
    _configure_logfire()
    # `logfire.span(...)` gives the run a named root span so the whole
    # request shows up under one collapsible node in the UI.
    with logfire.span("blog-post-run", topic="why uv is replacing pip"):
        result = await writer.run("Why uv is replacing pip for new Python projects")
    print(result.output)
    print("---")
    print(result.usage)


if __name__ == "__main__":
    asyncio.run(main())
