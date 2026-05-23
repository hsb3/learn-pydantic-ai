"""04 — Stateless tools (`@agent.tool_plain`).

Tools let the model call your Python functions to fetch information or
perform actions. The model decides when to call them based on the docstring
and parameter types.

Use `@agent.tool_plain` when the tool needs nothing from the run context.
Use `@agent.tool` (next example) when it needs deps, retries, or messages.

Note the docstrings: they're not just documentation — the model reads them
to decide when to call each tool. Write them clearly.
"""

from __future__ import annotations

import random

from pydantic_ai import Agent

from _common import FLASH


agent = Agent(
    FLASH,
    instructions=(
        "You play a dice game. Roll the die, then compare to the user's guess. "
        "Tell them whether they won."
    ),
)


@agent.tool_plain
def roll_dice() -> int:
    """Roll a six-sided die. Returns an integer 1-6."""
    return random.randint(1, 6)


@agent.tool_plain
def coin_flip() -> str:
    """Flip a fair coin. Returns 'heads' or 'tails'."""
    return random.choice(["heads", "tails"])


def main() -> None:
    random.seed(42)  # deterministic for demo
    result = agent.run_sync("My guess is 4. Also flip a coin while you're at it.")
    print(result.output)
    print("---")
    # all_messages() shows the full agent loop. Print just the part names
    # to see request → tool_call → tool_return → text without the noise.
    for msg in result.all_messages():
        kind = type(msg).__name__
        for part in msg.parts:
            label = type(part).__name__
            if label == "UserPromptPart":
                print(f"{kind:14} user: {part.content!r}")
            elif label == "ToolCallPart":
                print(f"{kind:14} call: {part.tool_name}({part.args})")
            elif label == "ToolReturnPart":
                print(f"{kind:14} return ({part.tool_name}): {part.content!r}")
            elif label == "TextPart":
                print(f"{kind:14} text: {part.content!r}")


if __name__ == "__main__":
    main()
