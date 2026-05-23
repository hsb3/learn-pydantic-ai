"""01 — Hello agent.

The smallest useful Pydantic AI program:
- pick a model with a `"provider:model"` string
- construct an `Agent`
- call `run_sync(prompt)` and read `result.output`

No tools, no structured output. Output is a plain string.
"""

from _common import FLASH
from pydantic_ai import Agent

agent = Agent(
    FLASH,
    instructions="Reply in one short sentence.",
)


def main() -> None:
    result = agent.run_sync('Where does "hello world" come from?')
    print(result.output)
    print("---")
    print(result.usage)


if __name__ == "__main__":
    main()
