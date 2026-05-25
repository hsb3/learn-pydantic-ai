# Lesson 14 — Observability with Logfire

**Code:** `14_logfire_observability.py`

## Goal
Get a tree-view trace of every agent call, tool call, and model request — without changing the agent code — by wiring [Logfire](https://logfire.pydantic.dev) into the run.

## Why it matters
By Lesson 11 you can stack agents three deep, and by Lesson 12 you have lifecycle Hooks that log individual events. Neither shows you the **shape** of a request: how the parent's call tree relates to the child's tool calls relates to the actual HTTP POST to Gemini. Logfire's nested-span view is the picture every other lesson has been describing in prose.

It's also the on-ramp to Track 02 Lesson 09, which uses the same instrumentation plus a `LogfirePlugin` to add Temporal workflow/activity spans on top of the pydantic-ai spans.

## Mental model
Three function calls turn on the observability. After that, every existing agent call gets traced automatically:

1. **`logfire.configure(...)`** — initialises the OpenTelemetry tracer for the process. `send_to_logfire="if-token-present"` is the graceful-degradation switch: with `LOGFIRE_TOKEN` set, traces ship to the cloud UI; without it, spans are still created (so the instrumentation is exercised) but the network exporter is a no-op.
2. **`logfire.instrument_pydantic_ai()`** — patches pydantic-ai so `Agent.run`, tool calls, and model requests emit spans.
3. **`logfire.instrument_httpx(capture_all=True)`** — bonus: each model request shows the actual HTTP POST as a child span, with headers, body, and timing.

You wrap a logical unit of work in `with logfire.span("name"):` to give it a named root in the UI. Everything underneath nests automatically.

## Walk the code

**`_configure_logfire`** does the three-call setup, then prints whether the token is set. This is the same shape Track 02 Lesson 09 uses.

```python
def _configure_logfire() -> None:
    logfire.configure(
        service_name="learn-pydantic-ai-lesson-14",
        send_to_logfire="if-token-present",
        scrubbing=False,
    )
    logfire.instrument_pydantic_ai()
    logfire.instrument_httpx(capture_all=True)
```

**`outliner` and `writer`** are the parent/child shape from Lesson 11 — kept deliberately familiar so the lesson is about Logfire's view, not about the agents themselves. `make_outline` is a `@writer.tool` that calls `outliner.run(..., usage=ctx.usage)`.

```python
@writer.tool
async def make_outline(ctx: RunContext[None], topic: str) -> Outline:
    """Plan an outline for the given topic. Returns title + bullet points."""
    result = await outliner.run(topic, usage=ctx.usage)
    return result.output
```

**`main`** runs the whole thing inside a `logfire.span(...)` so the UI groups every span under one collapsible "blog-post-run" node. Attributes you pass to the span (`topic=...`) show up as searchable structured fields.

```python
async def main() -> None:
    _configure_logfire()
    with logfire.span("blog-post-run", topic="why uv is replacing pip"):
        result = await writer.run("Why uv is replacing pip for new Python projects")
    print(result.output)
    print("---")
    print(result.usage)
```

## Run
```bash
make intro-14
```

With `LOGFIRE_TOKEN` set in `.env`, open <https://logfire.pydantic.dev>, pick the `learn-pydantic-ai-lesson-14` service, and find the trace named `blog-post-run`. You should see nesting along these lines:

```
blog-post-run
└── writer Agent.run
    ├── chat google:gemini-... (model request)
    │   └── POST generativelanguage.googleapis.com (httpx)
    ├── tool make_outline
    │   └── outliner Agent.run
    │       ├── chat google:gemini-... (model request)
    │       │   └── POST generativelanguage.googleapis.com
    │       └── ... (structured-output validation)
    └── chat google:gemini-... (final model request)
        └── POST generativelanguage.googleapis.com
```

Without a token, the script still prints the blog post and a `RunUsage(...)` line; Logfire just doesn't ship anything.

## Try it
1. **Add a fact-lookup tool.** Add `@writer.tool def lookup_release_date(ctx, package: str) -> str:` returning hard-coded data. Notice it gets its own span in the tree.
2. **Constrain the trace.** Wrap individual logical sub-steps in their own `logfire.span("...")` blocks — they nest under the parent run and let you search by sub-step name.
3. **Add attributes for filtering.** Pass extras to `logfire.span(..., user_id=42, locale="en-GB")`. They show up as columns in the Logfire UI and are filterable in queries.
4. **Disable HTTP span capture.** Remove `logfire.instrument_httpx(...)`. The trace tree shrinks — model-request spans no longer have the raw HTTP child. Useful when bodies contain sensitive data.

## Gotchas
- **Configure once, before any agent run.** Calling `logfire.configure(...)` inside a loop or per-request re-initialises the tracer and breaks nesting. The pattern is "call from `main()`, never from a request handler."
- **`send_to_logfire="if-token-present"` is the safe default.** Hard-setting `send_to_logfire=True` makes the SDK raise at startup if `LOGFIRE_TOKEN` is missing — fine for production, surprising for a lesson.
- **`scrubbing=False` keeps payloads readable.** The default scrubber redacts fields that look like secrets, which often eats useful debug info. Turn it back on if you'd ship traces containing user data.
- **`instrument_pydantic_ai()` is idempotent but cheap to be careful about.** Don't call it inside an agent's tool — it patches at module level and only needs to run once per process.

## Bridge
You can now see the call tree of any pydantic-ai code. That same instrumentation pattern composes with Temporal in [Track 02 Lesson 09](../../../02-temporal/lessons/09_observability/README.md): `LogfirePlugin` adds a wrapping `workflow` span and an `activity` span per generated activity, so the pydantic-ai spans you saw here nest one level deeper inside the durable history. Same `logfire.configure` + `logfire.instrument_pydantic_ai` setup; the plugin handles the rest.
