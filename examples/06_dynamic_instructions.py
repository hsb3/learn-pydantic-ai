"""06 — Dynamic instructions (`@agent.instructions`).

Static instructions go on `Agent(instructions=...)`. But sometimes the
prompt needs information you only have at run time: the current date,
the user's name, feature flags, A/B variants, etc.

`@agent.instructions` decorators run on every request and their return
values are appended to the system prompt. They can be sync or async,
and the ones taking `RunContext[DepsT]` can read deps.

This lesson also shows off the **`model=` per-call override**: one
agent definition, three different LLM providers. The dynamic
instructions are provider-agnostic — the same `@agent.instructions`
functions run regardless of which model is handling the request.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from pydantic_ai import Agent, RunContext

from _common import MODELS


@dataclass
class User:
    name: str
    locale: str  # e.g. "en-GB", "es-ES"


# No default model on the Agent — we'll pick one per call. This makes the
# provider-switching explicit; without `model=` on `run_sync(...)`, this
# call would fail.
agent = Agent[User, str](
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
    # Same agent, same instructions, three providers.
    runs: list[tuple[User, str]] = [
        (User(name="Henry", locale="en-GB"), "google"),
        (User(name="Lucía", locale="es-ES"), "anthropic"),
        (User(name="Yuki", locale="ja-JP"), "openai"),
    ]
    for user, provider in runs:
        model = MODELS[provider]["fast"]
        result = agent.run_sync(
            "What day is it tomorrow?",
            deps=user,
            model=model,  # per-call override; agent has no default
        )
        print(f"[{user.name} / {user.locale} via {provider}] {result.output}")


if __name__ == "__main__":
    main()
