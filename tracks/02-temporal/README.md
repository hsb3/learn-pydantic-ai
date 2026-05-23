# Track 02 — Durable agents with Temporal

**Status:** scaffolded; lesson content not yet written.

## What this track will cover

Building pydantic-ai agents whose state survives crashes, retries, and long human-in-the-loop pauses by running them inside a [Temporal](https://temporal.io/) workflow. The intro-track teaser at [`../01-intro/lessons/runtimes.md`](../01-intro/lessons/runtimes.md) lays out the trio (`TemporalAgent` / `PydanticAIWorkflow` / `PydanticAIPlugin`) and the workflow-vs-activity mental model. This track expands that into runnable lessons.

## Planned lesson outline

1. Local Temporal dev server + a minimal durable agent
2. Workflow vs activity — what pydantic-ai wraps automatically and what stays in the workflow context
3. Per-activity `activity_config` (retries, timeouts, heartbeats)
4. Streaming events out of a workflow to a UI via `event_stream_handler`
5. Human-in-the-loop pauses with `workflow.wait_condition` + signals
6. `TemporalRunContext` — what's different about `RunContext` inside a workflow
7. Long-running tools (file processing, scraping) as dedicated activities
8. Observability with Logfire's `LogfirePlugin`
9. Self-hosted vs Temporal Cloud — deployment notes

## When real lessons land here

- `examples/01_*.py` ... numbered like the intro track
- `lessons/01-*.md` ... matching one-pagers
- `tests/test_lessons.py` ... live smoke tests using a local `temporal server start-dev`
- A `worker.py` script + Makefile target to spin up the worker
