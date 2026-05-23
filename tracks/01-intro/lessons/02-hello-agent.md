# Lesson 02 — Hello agent

**Code:** `../examples/02_hello_agent.py`

## Goal
Construct the smallest possible Pydantic AI program: pick a model, build an `Agent`, call it, read the result.

## Why it matters
Every later lesson is a refinement of these four steps. Knowing exactly what an `Agent.run_sync()` call costs and returns is the foundation for everything else.

## Mental model
An **Agent** is a configured caller around an LLM. You hand it a model and instructions; you get back an object with `.output` (your answer), `.usage` (tokens), and `.all_messages()` (the full request/response transcript). That's it. No magic — until you start adding tools, capabilities, and structured output in the next lessons.

## Walk the code
- `learn_pydantic_ai/__init__.py` — exposes `FLASH = MODELS["google"]["fast"]`. Model strings are always `"provider:model-name"`. Without the provider prefix, pydantic-ai can't resolve the model.
- `../examples/02_hello_agent.py:16` — `Agent(FLASH, instructions=...)`. `instructions` is the system prompt.
- `../examples/02_hello_agent.py:23` — `agent.run_sync(prompt)` blocks until the model answers; `result.output` is a plain `str` because no `output_type` was set.
- `../examples/02_hello_agent.py:26` — `result.usage` shows token counts. Gemini's `thoughts_tokens` are internal reasoning tokens you pay for but never see.

## Run
```bash
uv run python ../examples/02_hello_agent.py
```
Expected: one sentence about "hello world", then a `RunUsage(...)` summary.

## Try it
1. Change `instructions=` to "Reply only in haiku." Rerun. Notice how the system prompt steers output.
2. Swap `FLASH` for `PRO` (`google:gemini-3-pro-preview`). Compare `output_tokens` and `thoughts_tokens`.
3. Read `result.all_messages()` — count how many `ModelRequest` and `ModelResponse` objects came back. (For a no-tool agent, it should be one of each.)

## Gotchas
- **Model string format is non-negotiable.** `"gemini-3-flash-preview"` (without `google:`) raises a resolution error.
- **`result.output` is the only thing typed as `str` by default.** Once you set `output_type=`, this becomes whatever Pydantic model you ask for (lesson 02).

## Bridge
Plain strings are brittle. Lesson 03 forces the model to return a validated Pydantic object instead.
