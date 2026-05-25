# Lesson 11 — Multi-agent delegation

**Code:** `11_multi_agent.py`

## Goal
Compose two agents — a parent that orchestrates, a child specialist it calls via a tool — with combined token-usage accounting.

## Why it matters
One mega-agent with 12 tools and a 4-paragraph system prompt fights itself. Splitting concerns into focused agents gives each one a tight prompt, a small tool surface, and (optionally) a different model. The parent stays in charge; the child returns a distilled answer.

## Mental model
A child agent is just another callable from the parent's perspective. You expose it as a `@parent.tool` that internally calls `child.run(...)`. The parent doesn't see the child's tool calls or reasoning — only the child's final output.

Critical detail: pass `usage=ctx.usage` when delegating so the parent's `RunUsage` accumulates the child's tokens too. Without it, you can't see what the inner run cost.

## Walk the code

**`outliner`** is the child: its own `output_type=Outline`, focused instructions, could be a different model from the parent.

```python
outliner = Agent(
    FLASH,
    output_type=Outline,
    instructions=(
        "Produce a tight outline: catchy title, 3-5 bullet points. "
        "Bullets are short noun phrases, no full sentences."
    ),
)
```

**`writer`** is the parent. Its instructions explicitly tell the model to call `make_outline` first — without that nudge the parent might skip the tool entirely.

```python
writer = Agent(
    FLASH,
    instructions=(
        "You write punchy short blog posts (3 paragraphs). "
        "Before writing, call `make_outline` to plan the structure, then "
        "write the post following the outline."
    ),
)
```

**`make_outline`** is a `@writer.tool` that internally calls the child. The tool's docstring is what the parent's model reads to know when to call it. `usage=ctx.usage` is the critical detail — without it, the child's tokens disappear from the parent's accounting.

```python
@writer.tool
async def make_outline(ctx: RunContext[None], topic: str) -> Outline:
    """Plan an outline for the given topic. Returns title + bullet points."""
    result = await outliner.run(topic, usage=ctx.usage)
    return result.output
```

## Run
```bash
uv run python 11_multi_agent.py
```
Expected: a 3-paragraph blog post, followed by a `RunUsage(... requests=3, tool_calls=1)` line (one parent request, one tool call into the child, one final parent request).

## Try it
1. Drop `usage=ctx.usage` and rerun. Parent `RunUsage` will undercount — the child's tokens disappear. That's the trap to avoid.
2. Give `outliner` a different model (`PRO` instead of `FLASH`). The parent's token budget now spans two model tiers — a common production pattern.
3. Add a second child — `editor` that critiques the draft. Have the parent call `make_outline` then `critique_draft`. You're now orchestrating two specialists.

## Gotchas
- **Forgotten `usage=ctx.usage`** is the most common bug. The run works fine; the accounting silently lies.
- **Watch for cycles.** Nothing prevents the child from calling back into the parent. It's expensive and rarely what you want.
- **Each child run is a fresh conversation.** Children don't inherit the parent's message history unless you pass `message_history=` explicitly.

## Bridge
You've built and composed agents in Python. Lesson 12 moves the configuration out of Python entirely — into YAML — and adds lifecycle hooks for observability.
