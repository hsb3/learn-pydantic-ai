# Learn Pydantic AI

A self-paced curriculum for the [Pydantic AI](https://ai.pydantic.dev/) agent framework. Twelve runnable examples + a matching one-page lesson, plus an API-tour reference lesson up front and a CLI-REPL capstone at the end.

## Key features

- **13 progressive lessons** — an API tour first, 11 examples introducing one concept each, then a CLI capstone
- **One-page lessons** in `lessons/` — mental model, code walkthrough, "try it" prompts, gotchas
- **Google Gemini throughout** — single provider, single API key
- **Makefile shortcuts** — `make lesson-NN`, `make repl`, `make nb-sync`, etc. (`make help` for the full list)
- **Real tests** — Lesson 10 ships `TestModel` + `FunctionModel` examples that pass under `pytest`

## Quick start

```bash
make install                                  # uv sync
cp .env.example .env                          # add your GOOGLE_API_KEY
make lesson-02                                # run any lesson by number
make repl                                     # drop into a chat REPL with cli_agent.yaml
```

Get a Gemini API key at <https://aistudio.google.com/apikey>. Run `make help` for the full task list.

## How to use this

Start at **[`lessons/00-orientation.md`](lessons/00-orientation.md)** — it explains the four-phase arc, recommends a study workflow, and tells you what to skip if you already know certain pieces.

For each lesson: read the one-pager → run the example → try a small modification → move on.

## Structure

```
examples/
  01_agent_api_tour.py    percent-style notebook for Lesson 01
  01_agent_api_tour.ipynb same content as .ipynb (open directly in Jupyter)
  02_hello_agent.py … 12_yaml_agent_with_hooks.py   scripts for Lessons 02-12
  agent.yaml              declarative spec used by Lesson 12
  _common.py              shared model strings + .env loader
lessons/
  00-orientation.md       curriculum map, study workflow
  01-agent-api-tour.md    reference tour of the Agent surface
  02-..12-..              paired with the example of the same number
```

The Lesson 01 notebook uses top-level `await` (canonical in Jupyter / VS Code interactive). The `.py` and `.ipynb` are paired via jupytext — edit either, then keep them in sync:

```bash
make nb-sync          # whichever file is newer wins
make nb-exec          # run the notebook end-to-end as a smoke test
make nb-clear         # strip cell outputs before committing
make nb-roundtrip     # sync + exec + clear, all at once
```

Open the `.ipynb` in VS Code's Jupyter extension or with `jupyter lab` (lab not bundled — install with `uv add --dev jupyterlab` if you want it).

## Lesson index

| # | Example | Concept |
|---|---------|---------|
| 01 | `01_agent_api_tour.py` (notebook) | Tour of `Agent`'s public API |
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
| 13 | `13_clai_agent_repl.py` (notebook) + `cli_agent.yaml` | Plug a YAML agent into `clai`; `make repl` |

Appendix: [`lessons/runtimes.md`](lessons/runtimes.md) — `clai`, `Agent.to_web/to_a2a/to_ag_ui`, and a Temporal teaser.

Run tests with `make test`. Run any individual lesson with `make lesson-NN`.

## Notes

Targets Pydantic AI **1.x**. Some 0.x APIs were renamed (e.g. `history_processors` → `ProcessHistory` capability; `StreamedRunResult.usage()` → property `.usage`).
