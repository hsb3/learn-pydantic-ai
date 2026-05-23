# Learn Pydantic AI — common tasks.
# Run `make` or `make help` to see what's available.

.DEFAULT_GOAL := help
.PHONY: help install nb-sync nb-exec nb-clear nb-roundtrip \
        repl repl-prompt repl-claude repl-claude-web \
        test test-all test-lessons test-clai test-live \
        dump-models clean

# ── auto-discover jupytext-paired notebooks across all tracks ──────────────
PAIRED_NB_PY := $(shell grep -l 'formats: ipynb' tracks/*/examples/*.py 2>/dev/null)
INTRO        := tracks/01-intro
CLAI_AGENT   := $(INTRO)/examples/cli_agent.yaml
CLAUDE_AGENT := $(INTRO)/examples/clai_anthropic.yaml

help:  ## Show this list of targets
	@awk 'BEGIN { FS = ":.*##"; printf "\nUsage: make <target>\n\nTargets:\n" } \
	      /^[a-zA-Z_%-]+:.*##/ { printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2 }' \
	      $(MAKEFILE_LIST)
	@printf "\nPer-lesson runners:\n"
	@printf "  \033[36mintro-NN\033[0m         Run an intro-track lesson, e.g. \`make intro-04\`\n"
	@printf "  \033[36mtemporal-NN\033[0m      Run a temporal-track lesson (when added)\n\n"

install:  ## Install / refresh all deps into .venv (also installs the local package editable)
	uv sync

# ── notebook workflow (auto-discovers across tracks) ───────────────────────
nb-sync:  ## Sync every paired .py <-> .ipynb (whichever side is newer wins)
	@for nb in $(PAIRED_NB_PY); do echo "→ $$nb"; uv run jupytext --sync $$nb; done

nb-exec:  ## Execute every paired .ipynb in-place (smoke test)
	@for nb in $(PAIRED_NB_PY); do \
		ipynb=$${nb%.py}.ipynb; echo "→ $$ipynb"; \
		uv run jupyter nbconvert --to notebook --execute --inplace $$ipynb --ExecutePreprocessor.timeout=180; \
	done

nb-clear:  ## Strip cell outputs from every paired .ipynb (do before committing)
	@for nb in $(PAIRED_NB_PY); do \
		ipynb=$${nb%.py}.ipynb; echo "→ $$ipynb"; \
		uv run jupyter nbconvert --clear-output --inplace $$ipynb; \
	done

nb-roundtrip: nb-sync nb-exec nb-clear  ## Sync, execute, clear — full pre-commit cycle

# ── REPL (uses intro track's YAML agents) ──────────────────────────────────
repl:  ## Start clai REPL with the intro track's default agent
	uv run --env-file .env pai --agent $(CLAI_AGENT)

repl-prompt:  ## One-shot: `make repl-prompt P="your question"`
	@if [ -z "$(P)" ]; then echo "Usage: make repl-prompt P=\"your question\""; exit 1; fi
	uv run --env-file .env pai --agent $(CLAI_AGENT) "$(P)"

repl-claude:  ## clai REPL with Claude Sonnet 4.6 + native web_search + code_execution
	uv run --env-file .env pai --agent $(CLAUDE_AGENT)

repl-claude-web:  ## clai web UI with Claude Sonnet 4.6 + native tools (no YAML needed)
	uv run --env-file .env pai web \
	  -m anthropic:claude-sonnet-4-6 \
	  -t web_search -t code_execution \
	  --port 8001

# ── per-track lesson runners (pattern rules) ───────────────────────────────
# `make intro-04`, `make intro-10` (pytest), `make intro-01` (notebook)
intro-%:
	@file=$$(ls $(INTRO)/examples/$**.py 2>/dev/null | head -1); \
	if [ -z "$$file" ]; then \
		echo "No example file matching $(INTRO)/examples/$**.py"; exit 1; \
	elif head -3 "$$file" | grep -q "jupyter:"; then \
		ipynb=$${file%.py}.ipynb; \
		echo "Intro lesson $* is a paired notebook ($$ipynb)."; \
		echo "Open in VS Code or run: make nb-exec"; \
	elif [ "$*" = "10" ]; then \
		uv run pytest "$$file" -v; \
	else \
		uv run python "$$file"; \
	fi

# Reserved for tracks/02-temporal/ once content lands.
temporal-%:
	@file=$$(ls tracks/02-temporal/examples/$**.py 2>/dev/null | head -1); \
	if [ -z "$$file" ]; then \
		echo "tracks/02-temporal/ — no example $* yet. See tracks/02-temporal/README.md"; exit 1; \
	else \
		uv run python "$$file"; \
	fi

# ── tests ──────────────────────────────────────────────────────────────────
test:  ## Run the intro Lesson 10 test file (fast, mocked)
	uv run pytest $(INTRO)/examples/10_testing.py -v

test-all:  ## Discover and run every test under tracks/*/examples (fast, mocked)
	uv run pytest tracks/*/examples/ -v

test-lessons:  ## Live smoke test — every intro lesson via `make intro-NN` (hits real APIs)
	uv run pytest $(INTRO)/tests/test_lessons.py -v

test-clai:  ## Live smoke test — both YAML-defined clai agents incl. Anthropic native tools
	uv run pytest $(INTRO)/tests/test_clai_agents.py -v

test-live: test-lessons test-clai  ## Every live test (lessons + clai agents)

# ── model lookup ───────────────────────────────────────────────────────────
dump-models:  ## Regenerate data/models.json (lookup table of valid provider:model strings)
	uv run python scripts/dump_models.py

# ── housekeeping ───────────────────────────────────────────────────────────
clean:  ## Remove caches and build cruft
	rm -rf .pytest_cache tracks/*/examples/__pycache__ tracks/*/examples/.ipynb_checkpoints
