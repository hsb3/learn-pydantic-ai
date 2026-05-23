# Lesson 06 — Dynamic instructions

**Code:** `examples/06_dynamic_instructions.py`

## Goal
Make the system prompt itself respond to runtime data — current date, user identity, feature flags — using `@agent.instructions`.

## Why it matters
A static `instructions="..."` string burns in everything at construction time. But you usually want "*Address the user by name*" or "*Today is …*". Hardcoding those into the prompt means rebuilding the agent for every user. `@agent.instructions` solves this cleanly: each decorated function runs per request, and its return value is appended to the system prompt.

## Mental model
Three kinds of instruction sources, evaluated and concatenated on every run:

1. The static `instructions=` string passed to `Agent(...)`.
2. Each `@agent.instructions` function with no params — pure dynamic facts (date, build version).
3. Each `@agent.instructions` function taking `RunContext[DepsT]` — facts that depend on this request's deps.

All three end up in the system prompt before the user message goes to the model.

## Walk the code
- `examples/06_dynamic_instructions.py:31` — Static instructions on the Agent (inside the `Agent[...]` constructor).
- `examples/06_dynamic_instructions.py:35` — `@agent.instructions` with a `RunContext[User]` — reads `ctx.deps.name`.
- `examples/06_dynamic_instructions.py:45` — `@agent.instructions` with no params — for facts that don't depend on deps (today's date).
- `examples/06_dynamic_instructions.py:52` — The same agent, different deps → different prompt → different language out.

## Run
```bash
uv run python examples/06_dynamic_instructions.py
```
Expected: an English reply for Henry, a Spanish reply for Lucía — same agent.

## Try it
1. Add an `async def` `@agent.instructions` that awaits a fake "feature flag" lookup. Async instructions work just like sync ones.
2. Remove one of the decorators and see which behaviour disappears in the output.
3. Add a `@agent.instructions` that returns `""` when a condition isn't met. Empty strings are skipped — that's the idiomatic conditional-instruction pattern.

## Gotchas
- **Order isn't guaranteed important.** Don't rely on instructions to appear in any particular order; treat each as independent.
- **Don't put secrets in instructions.** Anything in the system prompt is sent to the provider. Use deps + tools for sensitive data; let the tool return only what's needed.
- **Per-request cost.** Every decorated function runs on every request. Heavy work belongs in a tool that the model calls when needed, not in `@agent.instructions`.

## Bridge
You now have full control of inputs to the model. Lesson 07 changes how you consume *outputs* — token-by-token streaming instead of waiting for the full answer.
