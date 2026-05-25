# Lesson 05 — Dependency injection

**Code:** `05_deps_injection.py`

## Goal
Pass typed state (DBs, clients, user info) into tools using `deps_type` + `RunContext`.

## Why it matters
Tools need to talk to your system. Globals make tests painful and accidentally share state across requests. Pydantic AI's solution is the same pattern as FastAPI's `Depends`: declare what a tool needs, hand it in at run time.

## Mental model
Two changes from lesson 03:
1. `Agent[DepsT, OutputT](deps_type=DepsT, …)` parameterises the agent with the deps type.
2. Tools are decorated with `@agent.tool` (no `_plain`) and take `ctx: RunContext[DepsT]` as the first parameter. Inside, `ctx.deps` is the value you passed to `run_sync(..., deps=...)`.

Same agent, different deps per call. Same loop as before; only the tool signature changes.

## Coming from LangChain / LangGraph?

Pydantic AI splits what LangGraph treats as one bag into two channels:

- **Construction time** — `model`, `output_type`, `deps_type`, `tools`, `capabilities`, static `instructions`. Set once. Stable. Reused for every request.
- **Run time** — every `run*()` method takes the same set of kwargs. `deps=` is the workhorse; the rest cover overrides, accounting, and history.

Per-run kwargs you can pass to `run` / `run_sync` / `run_stream*`:

```python
agent.run_sync(
    prompt,
    deps=...,              # main channel — typed via deps_type
    message_history=...,   # prior conversation (Lesson 09)
    model=...,             # one-call model override
    model_settings=...,    # provider knobs for this call
    usage=...,             # share token accounting (Lesson 11)
    usage_limits=...,
    capabilities=[...],    # additive
    toolsets=[...],        # additive
    metadata=...,
    event_stream_handler=...,
)
```

Translation table:

| LangChain / LangGraph | Pydantic AI |
|---|---|
| `config={"configurable": {"user_id": ...}}` | `deps=MyDeps(user_id=...)` — typed dataclass enforced by `deps_type` |
| `config={"thread_id": ...}` + checkpointer | `message_history=prior.all_messages()` |
| `RunnableConfig.metadata` / `.tags` | `metadata=...` per-run |
| Rebuilding the chain to swap a model | `agent.run_sync(prompt, model=other_model)` — one-call override, no rebuild |
| `astream_events()` for progress UI | `event_stream_handler=` callback, or `run_stream_events()` |
| `chain.with_config(...)` to bind state | `agent.override(...)` — but ONLY for test substitution / A/B swaps, not for normal dynamic context |

You almost never mutate `agent.model`, `agent.instructions`, etc. — there's no supported setter pattern. Build once at module import; reuse forever.

## Walk the code
- `05_deps_injection.py:24` — `CustomerDB` is just a dataclass standing in for a real client. The type matters; the implementation doesn't.
- `05_deps_injection.py:34` — `Agent[CustomerDB, str](FLASH, deps_type=CustomerDB, ...)`. The generic and the runtime `deps_type=` say the same thing; together they give you static + runtime safety.
- `05_deps_injection.py:44` — `@agent.tool` (not `tool_plain`). First param is `ctx: RunContext[CustomerDB]`.
- `05_deps_injection.py:70` — `agent.run_sync(..., deps=db)` is where the dependency actually arrives.

## Run
```bash
uv run python 05_deps_injection.py
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
