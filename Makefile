# Learn Pydantic AI — common tasks.
# Run `make` or `make help` to see what's available.

.DEFAULT_GOAL := help
.PHONY: help install nb-sync nb-exec nb-clear nb-roundtrip repl repl-prompt test test-all clean

# ── auto-discover jupytext-paired notebooks (those with a jupytext header) ──
PAIRED_NB_PY := $(shell grep -l 'formats: ipynb' examples/*.py 2>/dev/null)
CLAI_AGENT   := examples/cli_agent.yaml

help:  ## Show this list of targets
	@awk 'BEGIN { FS = ":.*##"; printf "\nUsage: make <target>\n\nTargets:\n" } \
	      /^[a-zA-Z_%-]+:.*##/ { printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2 }' \
	      $(MAKEFILE_LIST)
	@printf "\nPer-lesson runner:\n  \033[36mlesson-NN\033[0m       Run lesson NN, e.g. \`make lesson-04\`\n\n"

install:  ## Install / refresh all deps into .venv
	uv sync

# ── notebook workflow ──────────────────────────────────────────────────────
nb-sync:  ## Sync every paired .py <-> .ipynb (whichever side is newer wins)
	@for nb in $(PAIRED_NB_PY); do echo "→ $$nb"; uv run jupytext --sync $$nb; done

nb-exec:  ## Execute every paired .ipynb in-place (smoke test; outputs land in .ipynb)
	@for nb in $(PAIRED_NB_PY); do \
		ipynb=$${nb%.py}.ipynb; \
		echo "→ $$ipynb"; \
		uv run jupyter nbconvert --to notebook --execute --inplace $$ipynb --ExecutePreprocessor.timeout=180; \
	done

nb-clear:  ## Strip cell outputs from every paired .ipynb (do before committing)
	@for nb in $(PAIRED_NB_PY); do \
		ipynb=$${nb%.py}.ipynb; \
		echo "→ $$ipynb"; \
		uv run jupyter nbconvert --clear-output --inplace $$ipynb; \
	done

nb-roundtrip: nb-sync nb-exec nb-clear  ## Sync, execute, clear — full pre-commit cycle

# ── REPL ───────────────────────────────────────────────────────────────────
repl:  ## Start clai REPL with the project default agent (examples/cli_agent.yaml)
	uv run --env-file .env pai --agent $(CLAI_AGENT)

repl-prompt:  ## One-shot: `make repl-prompt P="your question"`
	@if [ -z "$(P)" ]; then echo "Usage: make repl-prompt P=\"your question\""; exit 1; fi
	uv run --env-file .env pai --agent $(CLAI_AGENT) "$(P)"

# ── per-lesson runner (pattern rule: `make lesson-04`) ─────────────────────
lesson-%:
	@file=$$(ls examples/$**.py 2>/dev/null | head -1); \
	if [ -z "$$file" ]; then \
		echo "No example file matching examples/$**.py"; exit 1; \
	elif head -3 "$$file" | grep -q "jupyter:"; then \
		ipynb=$${file%.py}.ipynb; \
		echo "Lesson $* is a paired notebook ($$ipynb)."; \
		echo "Open in VS Code or run: make nb-exec"; \
	elif [ "$*" = "10" ]; then \
		uv run pytest "$$file" -v; \
	else \
		uv run python "$$file"; \
	fi

# ── tests ──────────────────────────────────────────────────────────────────
test:  ## Run the Lesson 10 test file
	uv run pytest examples/10_testing.py -v

test-all:  ## Discover and run every test under examples/
	uv run pytest examples/ -v

# ── housekeeping ───────────────────────────────────────────────────────────
clean:  ## Remove caches and build cruft
	rm -rf .pytest_cache examples/__pycache__ examples/.ipynb_checkpoints
