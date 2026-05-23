# Learn Pydantic AI

A self-paced curriculum for the [Pydantic AI](https://ai.pydantic.dev/) agent framework. Eleven runnable examples + a matching one-page lesson for each.

## Key features

- **11 progressive examples** — one new concept per lesson, every example runs end-to-end
- **One-page lessons** in `lessons/` — mental model, code walkthrough, "try it" prompts, gotchas
- **Google Gemini throughout** — single provider, single API key
- **Real tests** — lesson 09 ships `TestModel` + `FunctionModel` examples that pass under `pytest`

## Quick start

```bash
uv sync                                       # install deps
cp .env.example .env                          # add your GOOGLE_API_KEY
uv run python examples/01_hello_agent.py
```

Get a Gemini API key at <https://aistudio.google.com/apikey>.

## How to use this

Start at **[`lessons/00-orientation.md`](lessons/00-orientation.md)** — it explains the four-phase arc, recommends a study workflow, and tells you what to skip if you already know certain pieces.

For each lesson: read the one-pager → run the example → try a small modification → move on.

## Structure

```
examples/         runnable .py files, one per lesson
  agent.yaml      declarative spec used by lesson 11
  _common.py      shared model strings + .env loader
lessons/          one-page markdown lesson per example
  00-orientation.md   start here
```

## Lesson index

| # | Example | Concept |
|---|---------|---------|
| 01 | `01_hello_agent.py` | `Agent`, `run_sync`, plain output |
| 02 | `02_structured_output.py` | `output_type=PydanticModel` |
| 03 | `03_simple_tools.py` | `@agent.tool_plain` |
| 04 | `04_deps_injection.py` | `deps_type`, `RunContext`, `@agent.tool` |
| 05 | `05_dynamic_instructions.py` | `@agent.instructions` |
| 06 | `06_streaming.py` | `run_stream`, `stream_text(delta=True)` |
| 07 | `07_capabilities.py` | `Thinking`, native `WebSearch` |
| 08 | `08_message_history.py` | `message_history=` for multi-turn |
| 09 | `09_testing.py` | `TestModel`, `FunctionModel`, `agent.override()` |
| 10 | `10_multi_agent.py` | Parent agent delegates via a tool |
| 11 | `11_yaml_agent_with_hooks.py` | `Agent.from_file`, `Hooks` |

Run tests with `uv run pytest examples/09_testing.py -v`.

## Notes

Targets Pydantic AI **1.x**. Some 0.x APIs were renamed (e.g. `history_processors` → `ProcessHistory` capability; `StreamedRunResult.usage()` → property `.usage`).
