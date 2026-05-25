# Lesson 08 — Capabilities (Thinking, WebSearch)

**Code:** `08_capabilities.py`

## Goal
Compose reusable behavior bundles onto an agent — `Thinking` for extended reasoning, `WebSearch` for grounded answers — using `capabilities=[...]`.

## Why it matters
Every provider has its own knobs: Anthropic's extended thinking, OpenAI's reasoning models, Gemini's grounding/search. Re-implementing each per-provider would be miserable. Capabilities unify these into one API. Same agent code; portable across providers.

## Mental model
A **capability** is an installable piece of behavior — it can register tools, hooks, model settings, instructions, or all of the above. You attach capabilities at construction time:

```python
Agent(MODEL, capabilities=[Thinking(effort="medium"), WebSearch()])
```

`Thinking` doesn't add a tool you call; it changes the provider request to allocate reasoning budget. `WebSearch` registers the provider's *native* search tool — no Python search code, no API key juggling. The model decides when to use it.

## Walk the code
- `08_capabilities.py:27` — `PRO` (gemini-3-pro-preview). Heavier-weight model for reasoning + tool use.
- `08_capabilities.py:32–36` — `capabilities=[Thinking(effort="medium"), WebSearch()]`.
- `08_capabilities.py:48` — Loop over `result.all_messages()` looking for `NativeToolCallPart`. **Native** capabilities use this part class, not the `ToolCallPart` used for your custom function tools.

## Run
```bash
uv run python 08_capabilities.py
```
Expected: a paragraph about a recent F1 race, with a source URL, and a `web_search → {'queries': [...]}` line showing the model actually searched.

## Try it
1. Drop `WebSearch()` from `capabilities`. Rerun. The model will either guess or hedge — confirming that the capability really was doing the lifting.
2. Switch `Thinking(effort="medium")` to `"high"`. Watch `thoughts_tokens` in the usage line balloon.
3. Constrain the search: `WebSearch(allowed_domains=["wikipedia.org"])` or `max_uses=2`. Ask a question that forces the constraint to bite.

## Gotchas
- **Native tools use `NativeToolCallPart`, not `ToolCallPart`.** If you're inspecting message parts and only checking for `ToolCallPart`, you'll miss native tool calls entirely.
- **Not every provider supports every capability.** `WebSearch` works on Google, Anthropic, and OpenAI but with different underlying APIs. Check the provider docs if you switch.
- **Thinking costs real tokens.** `thoughts_tokens` in `RunUsage` are billed even though you never see them in the output.

## Bridge
You can drive one rich run. Lesson 09 chains *many* runs into a conversation by passing message history forward.
