"""08 — Message history (multi-turn chat).

Agents are stateless across runs by default. To keep context across turns,
pass `message_history=` on subsequent runs.

- `result.new_messages()` → just the messages from the run that produced it
- `result.all_messages()` → the full history seen by that run

The usual chat-loop pattern: thread `new_messages()` from each result into
the next call.

When `message_history` is non-empty, Pydantic AI assumes the instructions
are already carried in the history — so the system prompt isn't re-added.
"""

from __future__ import annotations

from pydantic_ai import Agent

from _common import FLASH


agent = Agent(
    FLASH,
    instructions="You are a Socratic tutor. Reply in one short paragraph.",
)


def main() -> None:
    history = []  # list[ModelMessage]; starts empty

    for prompt in [
        "I want to learn what a monad is. Don't define it — ask me a question first.",
        "I do know what a list is in Python.",
        "OK, given that, what's a monad?",
    ]:
        print(f"\n>>> user: {prompt}")
        result = agent.run_sync(prompt, message_history=history)
        print(f"<<< agent: {result.output}")
        # Append only the *new* messages so we don't duplicate the prior turn.
        history = result.all_messages()

    print(f"\n(messages accumulated: {len(history)})")


if __name__ == "__main__":
    main()
