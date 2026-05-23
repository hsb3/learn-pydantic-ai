# Orientation

A short tour of how this curriculum is laid out and how to study it.

## The arc

The 13 lessons are grouped into five phases. Each phase has its own payoff — you can stop after any phase and have something useful.

| Phase | Lessons | What you'll be able to do |
|-------|---------|---------------------------|
| **0 — Map** | 01 | Recognize every public class / decorator / method on the `Agent` API. No code yet — pure reference. |
| **1 — Foundations** | 02, 03 | Build an agent that returns plain text or a validated Pydantic model. |
| **2 — Tools & state** | 04, 05, 06 | Give an agent abilities (tools), runtime context (deps), and dynamic prompts. |
| **3 — Production runtime** | 07, 08, 09 | Stream tokens, plug in native capabilities (search, thinking), hold a multi-turn conversation. |
| **4 — Engineering** | 10, 11, 12 | Write deterministic tests, delegate between agents, drive agents from YAML with lifecycle hooks. |
| **5 — Putting it together** | 13 | Wire a YAML-defined agent into the `clai` REPL; `make repl` becomes your daily-use loop. |

## How to study each lesson

Each lesson is ~300 words (the tour in Lesson 01 is longer because it's reference) and pairs with one runnable file in `../examples/`. Lesson 01's companion is a Jupyter-style notebook (`01_agent_api_tour.py` / `.ipynb`) so you can poke the API live; Lessons 02-12 ship as scripts. The pattern that works:

1. **Read** the one-pager top to bottom (90 seconds; 5 minutes for the tour).
2. **Predict** what the example will print before you run it.
3. **Run** the example. From the repo root: `make intro-NN` (for Lesson 01 / 13 — notebooks — that prints a pointer; open in VS Code or run `make nb-exec`).
4. **Modify** — do at least one "Try it" prompt. The friction of a small edit is where the concept sticks.
5. **Move on** when the "Bridge" section tells you what's next.

Resist the urge to read all 12 in a row. The lessons assume you've actually run the code from the previous one.

## Prerequisites

- Python 3.13 + `uv` (installed by `mise` if you use my setup)
- `GOOGLE_API_KEY` in `.env` (get one at <https://aistudio.google.com/apikey>)
- Comfort with Python type hints, dataclasses, and `async`/`await` (lesson 07 onwards uses async)

## Skip-ahead matrix

If you already know… | …jump to
---|---
What an agent is, but not pydantic-ai specifically | Lesson 01 (tour), then 04
LangChain / LlamaIndex tool patterns | Lesson 01 (tour), then 05
How to call LLMs but never built a multi-turn chat | Lesson 09
Everything except testing/production patterns | Lesson 10

## Vocabulary you'll see repeatedly

- **Agent** — the orchestrator: model + instructions + tools + capabilities, bound by an output type.
- **Tool** — a Python function the model can call mid-run. `@agent.tool_plain` for stateless, `@agent.tool` for stateful.
- **RunContext** — the per-run handle a tool receives, carrying `deps`, `usage`, message history.
- **deps / `deps_type`** — typed state you inject into a run (DB handles, user info, request scope).
- **Capability** — a reusable behavior bundle. `Thinking`, `WebSearch`, `Hooks`, `ProcessHistory` are all capabilities.
- **Hook** — a decorator-registered callback into the agent loop (before model request, before tool execute, on error…).

Start with [Lesson 01 — Agent API tour](./01-agent-api-tour.md).

## Appendix

- [`runtimes.md`](./runtimes.md) — identity (`clai`, `Agent.to_web/to_cli/to_a2a/to_ag_ui`) and a teaser on durable agents with Temporal. Read after Lesson 12 when you're thinking about hosting or crash-safety.
