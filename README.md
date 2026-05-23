# Learn Pydantic AI

A self-paced curriculum for the [Pydantic AI](https://ai.pydantic.dev/) agent framework. Eleven runnable examples + a matching one-page lesson, plus an API-tour reference lesson up front.

## Key features

- **12 progressive lessons** — an API tour first, then 11 examples that introduce one concept each
- **One-page lessons** in `lessons/` — mental model, code walkthrough, "try it" prompts, gotchas
- **Google Gemini throughout** — single provider, single API key
- **Real tests** — Lesson 10 ships `TestModel` + `FunctionModel` examples that pass under `pytest`

## Quick start

```bash
uv sync                                       # install deps
cp .env.example .env                          # add your GOOGLE_API_KEY
uv run python examples/02_hello_agent.py
```

Get a Gemini API key at <https://aistudio.google.com/apikey>.

## How to use this

Start at **[`lessons/00-orientation.md`](lessons/00-orientation.md)** — it explains the four-phase arc, recommends a study workflow, and tells you what to skip if you already know certain pieces.

For each lesson: read the one-pager → run the example → try a small modification → move on.

## Structure

```
examples/         runnable .py files (02-12); 01 is reference-only
  agent.yaml      declarative spec used by Lesson 12
  _common.py      shared model strings + .env loader
lessons/
  00-orientation.md      curriculum map, study workflow
  01-agent-api-tour.md   reference tour of the Agent surface
  02-..12-..             paired with the example of the same number
```

## Lesson index

| # | Example | Concept |
|---|---------|---------|
| 01 | *(reference)* | Tour of `Agent`'s public API |
| 02 | `02_hello_agent.py` | `Agent`, `run_sync`, plain output |
| 03 | `03_structured_output.py` | `output_type=PydanticModel` |
| 04 | `04_simple_tools.py` | `@agent.tool_plain` |
| 05 | `05_deps_injection.py` | `deps_type`, `RunContext`, `@agent.tool` |
| 06 | `06_dynamic_instructions.py` | `@agent.instructions` |
| 07 | `07_streaming.py` | `run_stream`, `stream_text(delta=True)` |
| 08 | `08_capabilities.py` | `Thinking`, native `WebSearch` |
| 09 | `09_message_history.py` | `message_history=` for multi-turn |
| 10 | `10_testing.py` | `TestModel`, `FunctionModel`, `agent.override()` |
| 11 | `11_multi_agent.py` | Parent agent delegates via a tool |
| 12 | `12_yaml_agent_with_hooks.py` | `Agent.from_file`, `Hooks` |

Run tests with `uv run pytest examples/10_testing.py -v`.

## Notes

Targets Pydantic AI **1.x**. Some 0.x APIs were renamed (e.g. `history_processors` → `ProcessHistory` capability; `StreamedRunResult.usage()` → property `.usage`).
