# Lesson 13 — A project-local `clai` agent (stub)

**Companion notebook:** `../examples/13_clai_agent_repl.py` (paired `.ipynb`).
**Spec:** `../examples/cli_agent.yaml`.

## Goal
Wire a YAML-defined agent into the `clai` REPL so `make repl` drops you into a chat with *your* tuned defaults — Gemini, terse, web-search on.

## Why it matters
Lessons 02-12 give you the building blocks. Lesson 13 is where you collect them into a *thing you can talk to*: one YAML file you can edit, one alias, no Python boilerplate every time you want to ask a question. This is the smallest practical "ship it" loop.

## Mental model
Three pieces:
1. **`../examples/cli_agent.yaml`** — your agent spec (the work of Lessons 02-08 distilled into declarative form).
2. **`clai` / `pai`** — the bundled REPL. It loads any agent passed via `--agent`.
3. **`make repl`** — convenience wrapper. Resolves to `make repl`.

No new pydantic-ai API to learn — Lesson 12 introduced `Agent.from_file()` and the CLI already calls it under the hood.

## Run
```bash
make repl                                  # interactive REPL
make repl-prompt P="What's new in uv?"     # one-shot prompt
```

`/help` inside the REPL lists slash-commands (`/multiline`, `/exit`, etc.).

## Try it
1. Edit `../examples/cli_agent.yaml` — change `effort: low` to `effort: medium`. Rerun `make repl` and ask a question that needs reasoning. Notice the `thoughts_tokens` go up.
2. Comment out `WebSearch` and ask "Who won the most recent Premier League match?". The agent will hedge or guess — confirming the capability really was doing the work.
3. Swap the model line to `google:gemini-3-pro-preview`. Compare answer quality vs cost.

## Stub status
This is intentionally minimal — the notebook just intros the agent and points at `make repl`. The wider hosting picture (web UI, A2A, durable execution) lives in [`runtimes.md`](./runtimes.md).

## Bridge
You've finished the curriculum. From here: read [`runtimes.md`](./runtimes.md), then circle back to whichever lesson you want to deepen — testing, message history, or the Temporal teaser that's waiting for a real deep dive.
