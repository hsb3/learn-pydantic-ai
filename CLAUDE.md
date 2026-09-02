# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

A track-based learning curriculum for the [Pydantic AI](https://ai.pydantic.dev/) agent framework. Targets pydantic-ai **2.x**, Python **3.13+**, managed with **uv**. This is teaching material — lessons are the product, not a library someone imports.

## Commands

Everything runs through the `Makefile` (`make help` lists all targets). All Python runs via `uv run`.

```bash
make install              # uv sync — installs deps + learn_pydantic_ai editable
make intro-NN             # run an intro lesson by number (e.g. make intro-04)
make temporal-NN          # run a temporal lesson's starter (worker must be up)
make temporal-NN-worker   # run a temporal lesson's worker (foreground, Ctrl-C to stop)
make dump-models          # regenerate data/models.json (after upgrading pydantic-ai)
```

### Tests

```bash
make test                 # fast — intro Lesson 10's mocked TestModel suite (only mocked test in the curriculum)
make test-lessons         # LIVE — every intro lesson, hits real APIs (~costs cents)
make test-clai            # LIVE — both YAML clai agents incl. Anthropic native tools
make test-lessons-temporal  # temporal lessons under WorkflowEnvironment.start_local() (no docker)
make test-live            # the full pre-push sweep (lessons + clai + temporal)
```

Run a single test: `uv run pytest tracks/02-temporal/tests/test_lesson_05.py -v`.

The **pre-push hook** (`lefthook.yml`) runs `make test-live` against real APIs. Bypass with `LEFTHOOK_EXCLUDE=test-live git push` or `git push --no-verify`. Requires one-time `lefthook install`.

### Temporal server (Track 02)

```bash
make temporal-up          # docker-compose: postgres + server + UI (:8080, gRPC :7233)
make temporal-status      # cluster health — should say SERVING
make temporal-down        # stop (keeps postgres volume)
make temporal-clean       # stop + wipe volume

make temporal-11-up       # capstone's OWN self-contained stack (Temporal + worker + FastAPI)
make temporal-11-curl     # scripted end-to-end demo
```

The base stack (`temporal-up`) and the capstone stack (`temporal-11-up`) both bind ports 7233/8080 — **never run both at once.**

## Architecture

### Shared package: `learn_pydantic_ai/`

Installed editable; every lesson imports from it instead of hard-coding strings or re-typing glue.

- `__init__.py` — `MODELS` dict (`{provider: {fast|smart: "provider:model"}}`) plus `FLASH`/`PRO` Google aliases. Loads `.env` **at import time**. **Validates every `MODELS` preset against `data/models.json` at import time** — a stale or typo'd model string raises immediately. After upgrading pydantic-ai, run `make dump-models` to refresh the catalog, then fix any presets that no longer validate.
- `temporal.py` — shared Temporal wiring: `connect()` (Client with `PydanticAIPlugin` pre-applied), `run_worker()`, `make_workflow_runner()`, and the `TASK_QUEUE`/`NAMESPACE`/`TEMPORAL_ADDRESS` constants (all `"learn-pydantic-ai"`).

### Two tracks, same layout

Both tracks use **co-located** lessons: each lesson is a directory
`tracks/<TRACK>/lessons/NN_<slug>/` containing the README (the lesson narrative)
and the runnable code side by side.

### Notebooks (jupytext-paired)

Intro lessons 01 & 13 and temporal lesson 01 are `.py` ↔ `.ipynb` pairs. The `.py` (percent-format, `# %%`) is the source of truth. `make nb-sync` aligns them, `make nb-exec` runs them headless (this is how notebook lessons are tested), `make nb-clear` strips outputs before committing.

### Reference docs

- `docs/temporal/` — Temporal explainers: `codec-server.md`, `workflow-requirements.md` (what the cluster needs from your code)
- `docs/pai-quickstart.md` — `pai`/`clai` CLI cheatsheet (binary is `pai`, help text says `clai`)
- `docs/runtimes.md` — pydantic-ai runtime surfaces (clai, `to_web/to_a2a/to_ag_ui`, Temporal teaser)
- `docs/dev_docs/` — authoring process: `LESSON-DEVELOPMENT-GUIDE.md`, `lesson-template.md`, `inspiration-notes.md` (patterns mined from reference repos), `ai_gen/` (point-in-time AI-generated planning docs)

### Lesson file decomposition

Single-file lessons by default. Split only when **(a)** Temporal sandbox isolation forces `workflows.py` apart from I/O-doing code, **(b)** a two-process study loop needs separate `worker.py` + `example.py`, **(c)** capstone complexity warrants role-based files (`agents/`, `activities.py`, …), or **(d)** an external framework consumes the file (`app.py` for uvicorn, `ui.py` for streamlit). Full rule: see `docs/dev_docs/LESSON-DEVELOPMENT-GUIDE.md` rule 3.6.

## Temporal gotchas (cost real debugging time)

- **Never pass `PydanticAIPlugin` to `Worker(...)`.** `connect()` applies it via the Client, and Temporal propagates client plugins to the worker. Passing it again double-registers the agents' auto-generated activities and crashes worker startup. `run_worker()`'s `extra_plugins` is for *non-client* plugins only (e.g. `LogfirePlugin` in Lesson 09).
- **Always use `make_workflow_runner()` on every `Worker` and in every test.** It adds `learn_pydantic_ai` to the sandbox passthrough list — required because the package does `Path(__file__).resolve()` + `load_dotenv()` at import time, both sandbox-restricted. `run_worker()` does this for you.
- **Determinism in workflow code** — no `random()`, `datetime.now()`, or network calls inside a `@workflow.defn` class. Those belong in activities.

## Authoring lessons

Track 02 lesson format, authoring rules, and the 7-step QC checklist are the living standard in **`docs/dev_docs/LESSON-DEVELOPMENT-GUIDE.md`**; the skeleton is `docs/dev_docs/lesson-template.md`. Key rules: the README and its `.py` files are one unit (change both in the same commit); "Walk the code" references symbols, never line numbers, with verbatim snippets; every lesson ships a test that runs its code end-to-end. Lesson READMEs are **exempt** from the 250–500 word README convention — they're teaching artifacts; cut for clarity, not length.

## Conventions

- `.env` holds `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` (see `.env.example`). Lessons run via `uv run --env-file .env`.
- Pick a model tier via `MODELS[provider][tier]` rather than hard-coding a `provider:model` string.
- `NOTES.md` is Henry's personal file — **do not edit without explicit permission** (it says so at the top).
