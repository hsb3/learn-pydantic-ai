# Track 01 — Intro

The 101: build a real pydantic-ai agent from `Agent(model)` through tests, multi-agent delegation, YAML-defined agents with lifecycle hooks, a `clai` REPL, and a Logfire-traced run.

## Where to start

Read **[`lessons/00_orientation/README.md`](lessons/00_orientation/README.md)** first — it explains the five-phase arc, the study workflow, and the skip-ahead matrix. Then work through the numbered lessons.

Each lesson is a directory `lessons/NN_<slug>/` containing the README and the runnable code side by side.

## Lesson index

| # | Lesson | Concept |
|---|--------|---------|
| 01 | [Agent API tour](lessons/01_agent_api_tour/README.md) (notebook) | Tour of `Agent`'s public API |
| 02 | [Hello agent](lessons/02_hello_agent/README.md) | `Agent`, `run_sync`, plain output |
| 03 | [Structured output](lessons/03_structured_output/README.md) | `output_type=PydanticModel` |
| 04 | [Simple tools](lessons/04_simple_tools/README.md) | `@agent.tool_plain` |
| 05 | [Deps injection](lessons/05_deps_injection/README.md) | `deps_type`, `RunContext`, `@agent.tool` |
| 06 | [Dynamic instructions](lessons/06_dynamic_instructions/README.md) | `@agent.instructions` + per-call `model=` switching |
| 07 | [Streaming](lessons/07_streaming/README.md) | `run_stream`, `stream_text(delta=True)` |
| 08 | [Capabilities](lessons/08_capabilities/README.md) | `Thinking`, native `WebSearch` |
| 09 | [Message history](lessons/09_message_history/README.md) | `message_history=` for multi-turn |
| 10 | [Testing](lessons/10_testing/README.md) | `TestModel`, `FunctionModel`, `agent.override()` |
| 11 | [Multi-agent](lessons/11_multi_agent/README.md) | Parent agent delegates via a tool |
| 12 | [YAML + hooks](lessons/12_yaml_agent_with_hooks/README.md) | `Agent.from_file`, `Hooks` |
| 13 | [clai agent REPL](lessons/13_clai_agent_repl/README.md) (notebook) | Plug a YAML agent into `clai`; `make repl` |
| 14 | [Logfire observability](lessons/14_logfire_observability/README.md) | `logfire.instrument_pydantic_ai()` — call-tree traces for any agent |

Appendix: [`docs/runtimes.md`](../../docs/runtimes.md) — `clai`, `Agent.to_web()`, the AG-UI adapter (with a keyless runnable example), and a Temporal teaser that leads into Track 02.

## Running lessons

From the repo root:

```bash
make intro-02              # any lesson by number
make intro-01              # notebooks print a pointer; open in VS Code or `make nb-exec`
make test                  # fast mocked tests for Lesson 10
make test-lessons          # live sweep — runs every lesson via `make intro-NN`
```

## Notebooks

Lessons 01 and 13 ship as `.py` ↔ `.ipynb` pairs (via `jupytext`). Use `make nb-sync` to keep them aligned, `make nb-exec` to execute headless, `make nb-clear` to strip outputs before committing.

## Imports

All lessons import shared helpers from the project-level package:

```python
from learn_pydantic_ai import MODELS, FLASH, PRO
```

`MODELS` is a `{provider: {tier: model_string}}` dict with `fast` and `smart` tiers for `anthropic`, `google`, and `openai`. `FLASH`/`PRO` are Google-tier aliases kept for back-compat with the original lessons.
