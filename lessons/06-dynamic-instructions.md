# Lesson 06 — Dynamic instructions

**Code:** `examples/06_dynamic_instructions.py`

## Goal
Make the system prompt itself respond to runtime data — current date, user identity, feature flags — using `@agent.instructions`. Along the way, see how `model=` swaps providers per call.

## Why it matters
A static `instructions="..."` string burns in everything at construction time. But you usually want "*Address the user by name*" or "*Today is …*". Hardcoding those into the prompt means rebuilding the agent for every user. `@agent.instructions` solves this cleanly: each decorated function runs per request, and its return value is appended to the system prompt.

Because the instructions are *provider-agnostic* (they're just Python returning strings), the same agent works against Anthropic, Google, or OpenAI without changes — only the `model=` kwarg on `run_sync(...)` switches the underlying LLM.

## Mental model
Three kinds of instruction sources, evaluated and concatenated on every run:

1. The static `instructions=` string passed to `Agent(...)`.
2. Each `@agent.instructions` function with no params — pure dynamic facts (date, build version).
3. Each `@agent.instructions` function taking `RunContext[DepsT]` — facts that depend on this request's deps.

All three end up in the system prompt before the user message goes to the model. The model handling it can be swapped per call via `model=`.

## Walk the code
- `examples/06_dynamic_instructions.py:34` — Agent has **no default model**. `run_sync(..., model=...)` is required; this makes provider-switching explicit.
- `examples/06_dynamic_instructions.py:41` — `@agent.instructions` with a `RunContext[User]` — reads `ctx.deps.name`.
- `examples/06_dynamic_instructions.py:51` — `@agent.instructions` with no params — for facts that don't depend on deps (today's date).
- `examples/06_dynamic_instructions.py:64` — Loop pairs each user with a different provider; `model=MODELS[provider]["fast"]` is the per-call override. Same `agent`, three LLMs.

## Run
```bash
make lesson-06
```
Expected: three replies, each in a different language, each from a different provider — same agent definition the whole time.

## Try it
1. Bump `"fast"` → `"smart"` on one of the providers. Notice the longer thinking / better grammar at higher cost.
2. Add an `async def` `@agent.instructions` that awaits a fake "feature flag" lookup. Async instructions work just like sync ones.
3. Add a `@agent.instructions` that returns `""` when a condition isn't met. Empty strings are skipped — that's the idiomatic conditional-instruction pattern.
4. Swap the three providers around (e.g., give Yuki Anthropic instead of OpenAI). The Japanese output won't change quality much — these tier-fast models are roughly comparable for short replies.

## Gotchas
- **Order isn't guaranteed important.** Don't rely on instructions to appear in any particular order; treat each as independent.
- **Don't put secrets in instructions.** Anything in the system prompt is sent to the provider. Use deps + tools for sensitive data; let the tool return only what's needed.
- **Per-request cost.** Every decorated function runs on every request. Heavy work belongs in a tool that the model calls when needed, not in `@agent.instructions`.
- **No-default-model pattern is opinionated.** Most lessons keep a default model on the Agent and only override `model=` when they actually need to swap. This lesson removes the default to make the provider-switching obvious. Either pattern is fine.

## Bridge
You now have full control of inputs to the model — including which model. Lesson 07 changes how you consume *outputs* — token-by-token streaming instead of waiting for the full answer.
