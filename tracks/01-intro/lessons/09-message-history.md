# Lesson 09 — Message history

**Code:** `../examples/09_message_history.py`

## Goal
Carry context across multiple `run_sync` calls to build a multi-turn conversation.

## Why it matters
Agents are stateless by default. Each `run_sync` is an isolated request — the model has no memory of the previous turn. To build a chatbot, scheduling assistant, or anything conversational, you need to manually thread the messages from one call into the next.

## Mental model
After each run, you have two views of the messages:

- `result.new_messages()` — only what happened in **this** run (user prompt + model output, plus any tool calls).
- `result.all_messages()` — the full conversation visible at the end of this run.

The chat-loop pattern: pass `result.all_messages()` as `message_history=` on the next `run_sync`. The model then sees the full back-and-forth.

When `message_history` is non-empty, pydantic-ai **does not** re-add the system prompt — it assumes the prior messages already carry the relevant context. If you change `instructions`, the change won't take effect mid-conversation unless you reset history.

## Walk the code
- `../examples/09_message_history.py:30` — `history = []` starts empty.
- `../examples/09_message_history.py:38` — `agent.run_sync(prompt, message_history=history)`. First iteration sends just the user prompt (no history); later iterations thread the prior turns.
- `../examples/09_message_history.py:41` — `history = result.all_messages()`. Overwriting (not appending) is the right move — `all_messages()` already includes the prior history.

## Run
```bash
uv run python ../examples/09_message_history.py
```
Expected: a 3-turn Socratic dialogue where each agent reply references prior context. Ends with `(messages accumulated: 6)` — 3 user prompts + 3 assistant responses.

## Try it
1. Replace `history = result.all_messages()` with `history += result.new_messages()`. Equivalent result, different mental model. Pick the one that fits your app.
2. After turn 2, *change* `agent.instructions` to "You are now grumpy." Notice it has no effect on the conversation, because the system prompt was already baked into history. To change persona mid-conversation, either drop history or use dynamic instructions (lesson 05).
3. Print `len(history)` after each turn. Watch it grow by 2 per turn (one request, one response).

## Gotchas
- **Token budget is finite.** A long conversation eventually exceeds the model's context window. For long-running chats, use the `ProcessHistory` capability to trim or summarise old messages.
- **System prompt suppression.** If your conversation history is non-empty, changing `instructions=` won't reach the model. Reset history or use dynamic `@agent.instructions`.
- **`new_messages()` vs `all_messages()`.** Easy to mix up. Rule: use `all_messages()` for what you'll pass forward; use `new_messages()` only when you want to log just this turn.

## Bridge
You now have a conversational agent. Lesson 10 makes it testable.
