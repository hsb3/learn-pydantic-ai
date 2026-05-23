# Learn Pydantic AI — common tasks.
# Run `make` or `make help` to see what's available.

.DEFAULT_GOAL := help
.PHONY: help install nb-sync nb-exec nb-clear nb-roundtrip test test-all clean

# ── single source of truth for the notebook ────────────────────────────────
NOTEBOOK := examples/01_agent_api_tour

help:  ## Show this list of targets
	@awk 'BEGIN { FS = ":.*##"; printf "\nUsage: make <target>\n\nTargets:\n" } \
	      /^[a-zA-Z_-]+:.*##/ { printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2 }' \
	      $(MAKEFILE_LIST)

install:  ## Install / refresh all deps into .venv
	uv sync

# ── notebook workflow ──────────────────────────────────────────────────────
nb-sync:  ## Sync paired .py <-> .ipynb (whichever is newer wins)
	uv run jupytext --sync $(NOTEBOOK).py

nb-exec:  ## Execute the notebook in-place — outputs land in the .ipynb
	uv run jupyter nbconvert --to notebook --execute --inplace \
		$(NOTEBOOK).ipynb --ExecutePreprocessor.timeout=180

nb-clear:  ## Strip cell outputs from the .ipynb (do this before committing)
	uv run jupyter nbconvert --clear-output --inplace $(NOTEBOOK).ipynb

nb-roundtrip: nb-sync nb-exec nb-clear  ## Sync, execute, then clear outputs — full pre-commit cycle

# ── tests ──────────────────────────────────────────────────────────────────
test:  ## Run the Lesson 10 test file
	uv run pytest examples/10_testing.py -v

test-all:  ## Discover and run every test under examples/
	uv run pytest examples/ -v

# ── housekeeping ───────────────────────────────────────────────────────────
clean:  ## Remove caches and build cruft
	rm -rf .pytest_cache examples/__pycache__ examples/.ipynb_checkpoints
