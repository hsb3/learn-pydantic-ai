# `pai` REPL quickstart

`pai` is the **C**ommand-**L**ine **AI** that ships with `pydantic-ai`. It's a thin CLI on top of `Agent`: pass a model or a YAML agent spec, get a REPL (or a one-shot, or a browser UI). Useful when you want to test an agent without writing any wrapper code.

> **TL;DR** — `uv run pai -m anthropic:claude-sonnet-4-6` drops you into a streaming REPL with that model. Add `-a <spec>` to use one of your YAML agents. Add `web` to get a browser UI.

## Try it

```sh
export ANTHROPIC_API_KEY=...
uv run pai -m anthropic:claude-sonnet-4-6
```

That's an interactive REPL. Type a prompt, get a streaming answer. `/help` inside the REPL lists slash-commands; `/exit` quits.

## One-shot vs REPL

Pass a prompt argument to skip the REPL and print one answer:

```sh
uv run pai -m anthropic:claude-sonnet-4-6 "What's the capital of Iceland?"
```

In this repo, `make repl-prompt P="…"` wraps this with the default YAML agent.

## Pick a model

```sh
uv run pai --list-models                                       # everything pydantic-ai knows about
uv run pai -m google-gla:gemini-2.5-flash                      # Google
uv run pai -m openai:gpt-5                                     # OpenAI
```

`provider:model` format. The full table that this curriculum standardizes on lives in [`learn_pydantic_ai/__init__.py`](../learn_pydantic_ai/__init__.py) (`MODELS`).

## Load a YAML agent

```sh
uv run --env-file .env pai --agent tracks/01-intro/lessons/13_clai_agent_repl/cli_agent.yaml
```

A YAML spec captures model + instructions + capabilities declaratively. Track 01's [Lesson 13](../tracks/01-intro/lessons/13_clai_agent_repl/README.md) walks through one.

The repo's `make repl` / `make repl-claude` targets are shortcuts for this — they point at the two YAML agents in lesson 13.

## Browser UI (`pai web`)

```sh
uv run pai web -m anthropic:claude-sonnet-4-6 \
  -t web_search -t code_execution \
  --port 8001
```

Different flag set from `pai`. Notable:

- `-m` is **repeatable** — first model is preselected, the rest appear as options in the UI
- `-t` here is for **provider-native tools**, not a theme — `code_execution`, `image_generation`, `web_fetch`, `web_search`, `x_search`
- `--agent` works the same way as in the REPL — point at a YAML spec

In this repo, `make repl-claude-web` is the canonical invocation.

## Flag cheatsheet

| Flag | Mode | What it does |
|---|---|---|
| `-m`, `--model` | both | Provider:model. Repeatable in `pai web`, single in `pai`. |
| `-a`, `--agent` | both | Path to YAML/JSON spec, or `module:variable`. |
| `-t`, `--code-theme` | `pai` | Pygments code theme for response rendering. Defaults to `dark`. |
| `-t`, `--tool` | `pai web` | Builtin provider tool (repeatable). |
| `-i`, `--instructions` | `pai web` | Extra system instructions layered on top of `--agent`'s. |
| `--no-stream` | `pai` | Disable streaming. Useful in tests / scripts. |
| `--port`, `--host` | `pai web` | Where the web UI binds. |
| `--list-models`, `-l` | `pai` | Print every model id pydantic-ai recognizes. |
