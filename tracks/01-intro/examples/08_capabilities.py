"""08 — Capabilities (Thinking, WebSearch).

Capabilities are reusable, composable bundles of agent behaviour. They
attach to an agent via `capabilities=[...]`. The two most common:

- `Thinking(effort='high'|'medium'|'low')`: lets the model do extended
  internal reasoning before producing output. Different providers expose
  this differently (Gemini's "thoughts", Anthropic's "extended thinking",
  OpenAI's reasoning models); pydantic-ai unifies it.

- `WebSearch()`: turns on the provider's *native* web-search tool, no
  custom tool code needed. The model decides when to search.

The two together → a research assistant that thinks hard and grounds its
answers with citations.
"""

from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.capabilities import Thinking, WebSearch

from learn_pydantic_ai import PRO


agent = Agent(
    PRO,  # Pro tier handles thinking + tool use better than flash
    instructions=(
        "You are a research assistant. Use web search when a question depends "
        "on recent or specific facts. Cite the source URLs you used."
    ),
    capabilities=[
        Thinking(effort="medium"),
        WebSearch(),
    ],
)


def main() -> None:
    result = agent.run_sync(
        "Who won the most recent Formula 1 race? Give one short paragraph "
        "with the date and a source URL."
    )
    print(result.output)
    print("---")
    # Native (provider-side) tool calls land as NativeToolCallPart, not the
    # ToolCallPart used for user-defined function tools.
    for msg in result.all_messages():
        for part in msg.parts:
            if type(part).__name__ == "NativeToolCallPart":
                print(f"  web_search → {part.args}")
    print(result.usage)


if __name__ == "__main__":
    main()
