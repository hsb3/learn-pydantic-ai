"""05 — Dynamic instructions (`@agent.instructions`).

Static instructions go on `Agent(instructions=...)`. But sometimes the
prompt needs information you only have at run time: the current date,
the user's name, feature flags, A/B variants, etc.

`@agent.instructions` decorators run on every request and their return
values are appended to the system prompt. They can be sync or async,
and the ones taking `RunContext[DepsT]` can read deps.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pydantic_ai import Agent, RunContext

from _common import FLASH


@dataclass
class User:
    name: str
    locale: str  # e.g. "en-GB", "es-ES"


agent = Agent[User, str](
    FLASH,
    deps_type=User,
    instructions="You are a polite scheduling assistant.",
)


@agent.instructions
def add_user_name(ctx: RunContext[User]) -> str:
    return f"Address the user by name: {ctx.deps.name}."


@agent.instructions
def add_locale(ctx: RunContext[User]) -> str:
    return f"Respond in the language matching locale {ctx.deps.locale}."


@agent.instructions
def add_today() -> str:
    # No RunContext param — this one doesn't need deps.
    return f"Today's date is {date.today().isoformat()}."


def main() -> None:
    for user in [
        User(name="Henry", locale="en-GB"),
        User(name="Lucía", locale="es-ES"),
    ]:
        result = agent.run_sync("What day is it tomorrow?", deps=user)
        print(f"[{user.name} / {user.locale}] {result.output}")


if __name__ == "__main__":
    main()
