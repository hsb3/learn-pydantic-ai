"""05 — Dependency injection (`@agent.tool` + `deps_type`).

`tool_plain` is great for stateless tools. Real applications need to pass
state: a DB connection, an HTTP client, a user ID, a request-scoped config.

Pydantic AI's solution: declare `deps_type` on the Agent, then write tools
that take a `RunContext[YourDepsType]` as the first arg. The deps you pass
to `run_sync(..., deps=...)` show up as `ctx.deps` inside every tool.

This keeps the agent itself pure (no globals), makes tools testable, and
gives you compile-time type checking via the generic parameter.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from learn_pydantic_ai import FLASH


@dataclass
class CustomerDB:
    """Stand-in for a real database connection or service client."""

    customers: dict[int, dict[str, str | float]]

    def get(self, customer_id: int) -> dict[str, str | float] | None:
        return self.customers.get(customer_id)


# Agent is parameterised by the deps type. Tools get type-checked access to it.
agent = Agent[CustomerDB, str](
    FLASH,
    deps_type=CustomerDB,
    instructions=(
        "You are a customer-support agent. Use the tools to look up account "
        "info. Be concise."
    ),
)


@agent.tool
def get_customer_balance(ctx: RunContext[CustomerDB], customer_id: int) -> float:
    """Return the current balance for the customer with the given id."""
    row = ctx.deps.get(customer_id)
    if row is None:
        raise ValueError(f"No customer with id {customer_id}")
    return float(row["balance"])


@agent.tool
def get_customer_name(ctx: RunContext[CustomerDB], customer_id: int) -> str:
    """Return the display name for the customer with the given id."""
    row = ctx.deps.get(customer_id)
    if row is None:
        raise ValueError(f"No customer with id {customer_id}")
    return str(row["name"])


def main() -> None:
    db = CustomerDB(
        customers={
            1: {"name": "Ada Lovelace", "balance": 123.45},
            2: {"name": "Alan Turing", "balance": -50.00},
        }
    )

    result = agent.run_sync(
        "What's the balance for customer 1? Give a friendly one-line answer.",
        deps=db,
    )
    print(result.output)


if __name__ == "__main__":
    main()
