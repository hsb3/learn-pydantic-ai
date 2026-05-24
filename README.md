# Learn Pydantic AI

A track-based curriculum + deep-dive examples for the [Pydantic AI](https://ai.pydantic.dev/) agent framework.

## Tracks

| Track | Status | What it covers |
|---|---|---|
| [`tracks/01-intro/`](tracks/01-intro/) | ✅ Complete | 13 progressive lessons — API tour → tools → deps → streaming → capabilities → testing → multi-agent → YAML + hooks → CLI REPL capstone. The 101. |
| [`tracks/02-temporal/`](tracks/02-temporal/) | ✅ Complete | Durable agents with Temporal — TemporalAgent + PydanticAIWorkflow, retries, streaming, HITL signals, long-running activities, Logfire observability, multi-agent capstone with FastAPI front-end. 11 lessons. |

More tracks (RAG, evals, MCP, deep observability) land here over time.

## Quick start

```bash
make install                                  # uv sync — also installs learn_pydantic_ai/ editable
cp .env.example .env                          # add GOOGLE_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY
lefthook install                              # one-time: wire the pre-push test gate
make intro-02                                 # run intro lesson 02
make repl                                     # chat REPL with the intro default agent
```

Run `make help` for every target.

## Shared layout

```
learn_pydantic_ai/        importable package — MODELS dict + .env loader (used by all tracks)
data/models.json          generated catalog of valid `provider:model` strings (make dump-models)
scripts/dump_models.py
tracks/
  01-intro/               examples/  lessons/  tests/
  02-temporal/            same shape (scaffolded)
Makefile                  per-track lesson runners: make intro-NN, make temporal-NN, ...
lefthook.yml              pre-push gate: runs make test-live
```

Within a track, the convention is:
- `examples/NN_<slug>.py` — runnable lesson code (numbered)
- `lessons/NN-<slug>.md` — paired one-page lesson doc
- `tests/` — pytest files for live smoke tests

## Daily-use commands

```bash
make intro-NN              # run an intro lesson by number
make temporal-NN           # run a temporal lesson (when added)
make repl                  # clai REPL, default agent
make repl-claude           # clai REPL with Claude Sonnet 4.6 + native web_search + code_execution
make nb-sync               # sync paired .py ↔ .ipynb notebooks
make test                  # fast mocked tests (lesson 10's TestModel suite)
make test-live             # full live sweep — 18 tests, ~2 min, hits real APIs
```

Pre-push hook runs `make test-live` automatically. Bypass with `git push --no-verify` or `LEFTHOOK_EXCLUDE=test-live git push`.

## Notes

Targets Pydantic AI **1.x**. The `learn_pydantic_ai` package validates the `MODELS` tier presets against `data/models.json` at import time — `make dump-models` to refresh after upgrading pydantic-ai.
