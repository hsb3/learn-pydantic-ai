# Lesson 10 — Testing with TestModel and FunctionModel

**Code:** `10_testing.py` *(run with `pytest`, not `python`)*

## Goal
Write deterministic, fast tests for agent behaviour without calling a real LLM.

## Why it matters
Real-model tests are slow, expensive, and flaky. You don't want CI burning $$$ to confirm that your tool wiring is correct. Pydantic AI ships two test doubles for exactly this.

## Mental model
Both doubles plug in via `agent.override(model=...)`, a context manager that swaps the model for the duration of the `with` block.

- **`TestModel()`** — auto-generates a *valid* response for whatever output type the agent expects, and invents plausible args for any tools. Use it for "does my agent wire up at all?" smoke tests.
- **`FunctionModel(fn)`** — you write `fn(messages, info) -> ModelResponse`. Full control over what the model "says". Use for asserting specific tool calls, simulating retries, or scripting multi-step exchanges.

Never set `agent.model = SomeModel()` directly. The override context manager is the only sanctioned way to swap; it restores the original on exit.

## Walk the code
- `10_testing.py:48` — `with weather_agent.override(model=TestModel()):` — three lines, zero assumptions about the real model.
- `10_testing.py:56` — `_scripted_model` inspects `messages` to decide whether the tool has already returned, then emits the next `ModelResponse`. This is the FunctionModel pattern: branch on the state of the conversation so far.
- `10_testing.py:69–76` — Note `tool_name="final_result"` for the structured output step. That's the auto-registered tool pydantic-ai uses to deliver typed output.

## Run
```bash
uv run pytest 10_testing.py -v
```
Expected: 3 tests pass in under a second. No network calls.

## Try it
1. Add a test that asserts `lookup_weather` is called exactly *twice* by scripting the FunctionModel to emit two tool calls. Use `result.all_messages()` to count.
2. Write a FunctionModel that raises an exception on the first call, returns normally on the second. Test that `Agent(retries=2, ...)` recovers.
3. Use `TestModel(custom_output_text='hello')` to constrain the auto-output for an agent without an `output_type`. Useful for tests that just check structural behaviour.

## Gotchas
- **`agent.override` is the ONLY supported swap.** Setting `agent.model = ...` works but bypasses the cleanup; tests will leak state.
- **`TestModel` invents arguments.** It doesn't care whether they make sense — if your test depends on specific tool args, use `FunctionModel`.
- **Structured output adds a hidden tool.** When you script a `FunctionModel` for a structured-output agent, you emit a call to `tool_name="final_result"` to deliver the output, not a `TextPart`.

## Bridge
You can build, run, and test single agents. Lesson 11 chains agents together — one agent calls another via a tool.
