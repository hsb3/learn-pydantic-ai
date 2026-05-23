# Lesson 01 — Agent API tour

**Companion notebook:** `../examples/01_agent_api_tour.py` — percent-style cells, open in VS Code (Python extension) or convert with `jupytext`. Poke each section as you read.

## Goal
Get oriented in `Agent`'s public surface before you start building.

## Why this lesson exists
You'll see the same names — `Agent(...)`, `@agent.tool`, `RunContext`, `run_stream`, `result.output` — over and over. Five minutes of pre-loading the whole surface makes every subsequent lesson land faster. You'll know which pieces are core, which are advanced, and what to ignore until you need it.

## Coming from LangChain / LangGraph?
The biggest mental shift: **the `Agent` is configured once at construction and stays stable.** Per-call dynamic context (user id, request scope, DB handles) does *not* go through "reconfigure then invoke." It flows through the run method's kwargs — primarily `deps=`, which is the typed equivalent of LangGraph's `config={"configurable": {...}}`.

You almost never mutate an agent's attributes between runs. Build once at module import, reuse for every request. Lesson 05 walks through this in detail and includes a translation table.

## The `Agent` constructor

```python
Agent(model, *,
      output_type=str,        # what `result.output` is typed as
      instructions=None,      # static system prompt
      deps_type=NoneType,     # type of ctx.deps
      tools=(),               # pre-registered tool list
      toolsets=None,          # grouped tools
      capabilities=None,      # behavior bundles (Thinking, WebSearch, Hooks, ...)
      model_settings=None,    # provider knobs (temperature, etc.)
      retries=None,           # auto-retry policy
      end_strategy='early',   # when the agent loop terminates
      tool_timeout=None,      # max seconds per tool call
      ...                     # name, description, metadata, validation_context,
                              # max_concurrency, defer_model_check — advanced
      )
```

| Kwarg | What it does | First seen |
|---|---|---|
| `model` | The LLM (model string `"google:..."` or instance) | Lesson 02 |
| `output_type` | Pydantic class for validated output | Lesson 03 |
| `instructions` | Static system prompt | Lesson 02 |
| `tools` / `@agent.tool*` | Functions the model can call | Lesson 04 |
| `deps_type` | Typed context injected into tools | Lesson 05 |
| `capabilities` | `Thinking`, `WebSearch`, `Hooks`, … | Lessons 08, 12 |
| `retries` | Retry policy on `ModelRetry` / tool errors | Lesson 05 (gotcha) |

Skipped on first read: `name`, `description`, `metadata`, `validation_context`, `max_concurrency`, `defer_model_check`, `system_prompt` (legacy alias for `instructions`).

## Decorators that register behavior

```python
@agent.tool_plain         # stateless tool, no RunContext param
@agent.tool               # stateful tool, takes RunContext[DepsT] as first arg
@agent.instructions       # dynamic system-prompt fragment (sync or async)
@agent.output_validator   # post-output validation hook
```

| Decorator | Use when | First seen |
|---|---|---|
| `@agent.tool_plain` | Pure function, no deps needed | Lesson 04 |
| `@agent.tool` | Tool needs deps, usage, or messages | Lesson 05 |
| `@agent.instructions` | Prompt fragment depends on runtime data | Lesson 06 |
| `@agent.output_validator` | Need to reject/transform `result.output` | (advanced) |

## Run methods (how you actually call the agent)

| Method | Sync? | Returns | Use when |
|---|---|---|---|
| `agent.run(prompt)` | async | `RunResult` | Async caller, full answer |
| `agent.run_sync(prompt)` | sync | `RunResult` | CLI / script / notebook |
| `agent.run_stream(prompt)` | async ctx mgr | `StreamedRunResult` | Token streaming |
| `agent.run_stream_sync(prompt)` | sync ctx mgr | `StreamedRunResult` | Sync streaming |
| `agent.run_stream_events(prompt)` | async iter | Typed `AgentStreamEvent`s | Custom event UIs |
| `agent.iter(prompt)` | async ctx mgr | Step-by-step control | Custom loops (advanced) |

All of them accept the same per-run kwargs: `deps=`, `message_history=`, `model=` (override), `model_settings=`, `usage=`, `usage_limits=`, `capabilities=` (additive), `toolsets=`, `event_stream_handler=`.

## Factories and overrides

| Method | What it does | First seen |
|---|---|---|
| `Agent.from_file(path, …)` | Load agent from YAML/JSON spec | Lesson 12 |
| `agent.override(model=, deps=, tools=, …)` | Context-manager swap (tests, A/B) | Lesson 10 |

## Result objects

**`RunResult`** — returned from `run` / `run_sync`:
- `.output` — typed answer (whatever `output_type=` said)
- `.usage` — `RunUsage(input_tokens, output_tokens, requests, tool_calls, …)`
- `.new_messages()` — messages added by this run
- `.all_messages()` — full conversation visible to this run

**`StreamedRunResult`** — yielded by the `run_stream*` context managers:
- `.stream_text(delta=True)` — async iter of *new* text chunks
- `.stream_text(delta=False)` — async iter of *accumulated* text
- `.stream_output()` — async iter of partial typed outputs
- `.stream_responses()` — async iter of raw `ModelResponse`s
- `.usage` — **property** (no parens; old code shows `.usage()` — deprecated in 1.x)
- `.all_messages()` — only after the `async with` block exits

## Supporting types you'll meet

- **`RunContext[DepsT]`** — the per-run handle passed to `@agent.tool`, `@agent.instructions`, hooks. Has `.deps`, `.usage`, `.messages`, `.retry`, more.
- **`RunUsage`** — token accounting. `thoughts_tokens` is what reasoning models burn internally.
- **`ModelMessage`** — abstract; concrete subclasses `ModelRequest` and `ModelResponse`. Each has a `.parts` list.
- **`*Part`** — the pieces inside a message: `UserPromptPart`, `TextPart`, `ToolCallPart` (your tools), `ToolReturnPart`, `NativeToolCallPart` (provider-native tools like web search). Inspecting parts is how you debug the agent loop.
- **`ModelRetry`** — exception you raise inside a tool to tell the model "try again with this hint."

## Deliberately NOT covered here

These exist but aren't day-one reading: `FallbackModel`, model-class subclasses, `ProcessHistory`, the full `Hooks` API, `pydantic_graph`. Each surfaces in the relevant lesson or in the [pydantic-ai docs](https://ai.pydantic.dev/).

## Bridge
Now you have the map. [Lesson 02 — Hello agent](./02-hello-agent.md) exercises the simplest path through it: `Agent(model) → run_sync(prompt) → result.output`.
