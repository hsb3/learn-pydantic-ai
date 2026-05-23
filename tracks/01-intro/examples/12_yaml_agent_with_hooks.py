"""12 — Agents from YAML + lifecycle hooks.

Two production-grade conveniences:

1. **`Agent.from_file`** lets ops/PMs edit prompts and capability bundles
   in YAML/JSON without touching Python. Template strings (`{{ name }}`)
   in `instructions` interpolate from `deps` at run time.

2. **`Hooks`** lets you intercept the agent loop without subclassing:
   - `before_model_request`: log/redact/swap requests before they hit the
     provider
   - `before_tool_execute`: audit or veto tool calls (great for HITL)
   - run-level, node-level, event-stream hooks also available

Hooks are a capability — attach with `capabilities=[hooks]` (here, layered
on top of capabilities already defined in the YAML).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pydantic_ai import Agent, RunContext
from pydantic_ai.capabilities.hooks import Hooks
from pydantic_ai.models import ModelRequestContext

from learn_pydantic_ai import (  # noqa: F401  -- loads .env for GOOGLE_API_KEY
    FLASH,
)


@dataclass
class UserContext:
    user_name: str
    today: str


# ── Lifecycle hooks: log every model request and tool call ─────────────────
hooks = Hooks()


@hooks.on.before_model_request
async def log_request(
    ctx: RunContext[UserContext],
    request_context: ModelRequestContext,
) -> ModelRequestContext:
    print(f"[hook] sending {len(request_context.messages)} messages to model")
    return request_context


@hooks.on.run_error
async def log_failure(ctx: RunContext[UserContext], error: BaseException) -> None:
    print(f"[hook] run failed: {type(error).__name__}: {error}")


# ── Load the agent from YAML, then layer Hooks on top ──────────────────────
agent = Agent.from_file(
    Path(__file__).parent / "agent.yaml",
    deps_type=UserContext,
    capabilities=[hooks],
)


def main() -> None:
    deps = UserContext(user_name="Henry", today=date.today().isoformat())
    result = agent.run_sync(
        "Give me one piece of advice for picking a Python web framework in 2026.",
        deps=deps,
    )
    print("---")
    print(result.output)


if __name__ == "__main__":
    main()
