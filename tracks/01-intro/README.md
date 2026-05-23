# Track 01 — Intro

The 101: build a real pydantic-ai agent from `Agent(model)` through tests, multi-agent delegation, YAML-defined agents with lifecycle hooks, and a `clai` REPL capstone.

## Where to start

Read **[`lessons/00-orientation.md`](lessons/00-orientation.md)** first — it explains the five-phase arc, the study workflow, and the skip-ahead matrix. Then work through the numbered lessons.

## Lesson index

| # | Example | Concept |
|---|---------|---------|
| 01 | `examples/01_agent_api_tour.py` (notebook) | Tour of `Agent`'s public API |
| 02 | `examples/02_hello_agent.py` | `Agent`, `run_sync`, plain output |
| 03 | `examples/03_structured_output.py` | `output_type=PydanticModel` |
| 04 | `examples/04_simple_tools.py` | `@agent.tool_plain` |
| 05 | `examples/05_deps_injection.py` | `deps_type`, `RunContext`, `@agent.tool` |
| 06 | `examples/06_dynamic_instructions.py` | `@agent.instructions` + per-call `model=` switching |
| 07 | `examples/07_streaming.py` | `run_stream`, `stream_text(delta=True)` |
| 08 | `examples/08_capabilities.py` | `Thinking`, native `WebSearch` |
| 09 | `examples/09_message_history.py` | `message_history=` for multi-turn |
| 10 | `examples/10_testing.py` | `TestModel`, `FunctionModel`, `agent.override()` |
| 11 | `examples/11_multi_agent.py` | Parent agent delegates via a tool |
| 12 | `examples/12_yaml_agent_with_hooks.py` | `Agent.from_file`, `Hooks` |
| 13 | `examples/13_clai_agent_repl.py` (notebook) + `examples/cli_agent.yaml` | Plug a YAML agent into `clai`; `make repl` |

Appendix: [`lessons/runtimes.md`](lessons/runtimes.md) — `clai`, `Agent.to_web/to_a2a/to_ag_ui`, and a Temporal teaser that leads into Track 02.

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

All examples import shared helpers from the project-level package:

```python
from learn_pydantic_ai import MODELS, FLASH, PRO
```

`MODELS` is a `{provider: {tier: model_string}}` dict with `fast` and `smart` tiers for `anthropic`, `google`, and `openai`. `FLASH`/`PRO` are Google-tier aliases kept for back-compat with the original lessons.
