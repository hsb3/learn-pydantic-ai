# Lesson 05 — Dependency injection

**Code:** `examples/05_deps_injection.py`

## Goal
Pass typed state (DBs, clients, user info) into tools using `deps_type` + `RunContext`.

## Why it matters
Tools need to talk to your system. Globals make tests painful and accidentally share state across requests. Pydantic AI's solution is the same pattern as FastAPI's `Depends`: declare what a tool needs, hand it in at run time.

## Mental model
Two changes from lesson 03:
1. `Agent[DepsT, OutputT](deps_type=DepsT, …)` parameterises the agent with the deps type.
2. Tools are decorated with `@agent.tool` (no `_plain`) and take `ctx: RunContext[DepsT]` as the first parameter. Inside, `ctx.deps` is the value you passed to `run_sync(..., deps=...)`.

Same agent, different deps per call. Same loop as before; only the tool signature changes.

## Walk the code
- `examples/05_deps_injection.py:24` — `CustomerDB` is just a dataclass standing in for a real client. The type matters; the implementation doesn't.
- `examples/05_deps_injection.py:34` — `Agent[CustomerDB, str](FLASH, deps_type=CustomerDB, ...)`. The generic and the runtime `deps_type=` say the same thing; together they give you static + runtime safety.
- `examples/05_deps_injection.py:44` — `@agent.tool` (not `tool_plain`). First param is `ctx: RunContext[CustomerDB]`.
- `examples/05_deps_injection.py:70` — `agent.run_sync(..., deps=db)` is where the dependency actually arrives.

## Run
```bash
uv run python examples/05_deps_injection.py
```
Expected: a friendly one-line answer mentioning Ada Lovelace and $123.45.

## Try it
1. Add a `get_overdue_customers(ctx)` tool that returns names with negative balance. Ask "Who owes money?" and watch the agent pick the right tool.
2. Pass a *different* `CustomerDB` to a second `run_sync` call — confirm the tools see the new data without rebuilding the agent.
3. Raise `ValueError` for an unknown id. The error surfaces as a run failure. Then swap to `from pydantic_ai import ModelRetry; raise ModelRetry("That id doesn't exist; ask the user to clarify.")` — observe how the model recovers gracefully.

## Gotchas
- **Don't mix decorators.** `@agent.tool_plain` with a `RunContext` param, or `@agent.tool` without one, both fail at runtime.
- **`deps_type` is for *what* not *how much*.** Make it a small dataclass holding handles, not a dict of loose values. Future-you (and the type checker) will thank you.
- **One deps instance per run.** If you mutate it inside a tool, that's visible to later tools in the same run — sometimes useful, often a footgun.

## Bridge
Static system prompts plus deps cover most cases. Lesson 06 lets the system prompt itself be dynamic.
