# Lesson 07 — Streaming

**Code:** `07_streaming.py`

## Goal
Receive output incrementally as the model produces it, instead of waiting for the full answer.

## Why it matters
Long responses can take 5–30 seconds. A chat UI that shows nothing until completion feels broken. Streaming lets you write tokens to the screen (or a websocket) the moment they arrive. Same cost; far better perceived latency.

## Mental model
`run_sync()` and `run_stream()` are siblings, not opposites:

- `run_sync` returns a `RunResult` after the run finishes.
- `run_stream` is an **async context manager** that yields a `StreamedRunResult`. Inside the `async with` block, you call `.stream_text(delta=True)` to get an async iterator of token chunks. When the block exits, the run is complete and `.usage` etc. are populated.

Streaming makes the call async — so a CLI entry point uses `asyncio.run(main())`.

## Walk the code

**`agent.run_stream(...)`** is an async context manager — the `async with` block guarantees the underlying provider stream is closed even on error. **`stream.stream_text(delta=True)`** is the async iterator; with `delta=True` each step is the *new* tokens, without it each step is the full accumulated text. **`stream.usage`** is a property in pydantic-ai 1.x (no parens).

```python
async with agent.run_stream("Describe a stormy seascape at dusk.") as stream:
    async for delta in stream.stream_text(delta=True):
        sys.stdout.write(delta)
        sys.stdout.flush()
    print()
    print("---")
    print(stream.usage)
```

## Run
```bash
uv run python 07_streaming.py
```
Expected: a vivid seascape description appearing chunk-by-chunk, then a `RunUsage(...)` line.

## Try it
1. Drop `delta=True`. You'll print the full text growing each step. Useful when the consumer needs the running total (e.g., rendering markdown).
2. Wrap the loop body in `await asyncio.sleep(0.01)` to artificially slow it down and watch the streaming behaviour.
3. Use `stream.stream_output()` with an `output_type=PydanticModel` agent — you get incremental partial-model updates as the structured output is filled in.

## Gotchas
- **`stream.usage` is a property in 1.x.** Older docs/code shows `stream.usage()` — that emits a `PydanticAIDeprecationWarning` and will be removed in v2.
- **You must consume the stream inside the `async with` block.** Outside the block, the underlying connection is closed.
- **Streaming + structured output need `stream_output()`**, not `stream_text()` — text streaming on a structured-output agent gives you the raw JSON being built, which isn't usually what you want.

## Bridge
You've controlled inputs and outputs. Lesson 08 unlocks provider-native superpowers — thinking and web search — without writing a single tool yourself.
