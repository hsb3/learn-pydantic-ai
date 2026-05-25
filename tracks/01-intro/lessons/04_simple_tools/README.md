# Lesson 04 — Simple tools

**Code:** `04_simple_tools.py`

## Goal
Let the model call your Python functions mid-run, using `@agent.tool_plain` for stateless tools.

## Why it matters
Without tools, an agent is a clever autocomplete. With tools, it can roll dice, query databases, send emails, hit APIs — anything Python can do. Tools are the bridge between the model's reasoning and your real system.

## Mental model
A run is a *loop*: the model can answer, **or** it can call one of your tools. If it calls a tool, pydantic-ai runs the Python function, feeds the return value back into the next model turn, and lets the model decide again. The loop ends when the model produces final text (or a structured output).

`@agent.tool_plain` is for tools that need nothing from the run — pure functions. The docstring + parameter types become the tool's schema, which the model reads to decide *when* to call it.

## Walk the code

**`roll_dice`** is registered with `@agent.tool_plain` — no `RunContext` parameter. The docstring is what the model reads to decide when to call it; write it as prompt copy, not implementation notes.

```python
@agent.tool_plain
def roll_dice() -> int:
    """Roll a six-sided die. Returns an integer 1-6."""
    return random.randint(1, 6)
```

**`coin_flip`** has the same shape — second tool, also stateless.

```python
@agent.tool_plain
def coin_flip() -> str:
    """Flip a fair coin. Returns 'heads' or 'tails'."""
    return random.choice(["heads", "tails"])
```

**The transcript loop** over `result.all_messages()` prints each part in turn — `UserPromptPart` → `ToolCallPart` → `ToolReturnPart` → `TextPart`. This is the agent loop made visible.

```python
for msg in result.all_messages():
    kind = type(msg).__name__
    for part in msg.parts:
        label = type(part).__name__
        if label == "UserPromptPart":
            print(f"{kind:14} user: {part.content!r}")
        elif label == "ToolCallPart":
            print(f"{kind:14} call: {part.tool_name}({part.args})")
        ...
```

## Run
```bash
uv run python 04_simple_tools.py
```
Expected output ends with a sentence about whether you won, plus a transcript showing both tools were called.

## Try it
1. Add a `@agent.tool_plain` named `magic_8_ball` that returns a random one-liner. Ask the agent for a prediction; watch it pick which tool to call.
2. Change the dice docstring to `"""Roll a die. Always returns 1."""` and watch how the *description* (not the implementation) changes the model's decision-making.
3. Remove `instructions=` from the Agent. Rerun. The agent still works but is less directed — see how the system prompt anchors tool use.

## Gotchas
- **`@agent.tool_plain` must NOT take `RunContext`** as its first argument. That's lesson 04's territory.
- **The model reads docstrings as instructions.** A vague or missing docstring leaves the model guessing when to call your tool.
- **Tools can raise.** An uncaught exception ends the run. To let the model retry, raise `ModelRetry("hint for the model")` instead.

## Bridge
Stateless tools are pure functions. Real apps need to pass DB connections, user IDs, config. Lesson 05 adds typed dependency injection.
