# Learn Pydantic AI — common tasks.
# Run `make` or `make help` to see what's available.

.DEFAULT_GOAL := help
.PHONY: help install nb-sync nb-exec nb-clear nb-roundtrip \
        repl repl-prompt repl-claude repl-claude-web \
        test test-all test-lessons test-clai test-live \
        test-lessons-temporal test-against-local-server \
        temporal-up temporal-down temporal-clean temporal-ui temporal-status \
        temporal-11-up temporal-11-down temporal-11-clean temporal-11-build \
        temporal-11-logs temporal-11-api temporal-11-curl temporal-11-ui \
        dump-models clean

# ── auto-discover jupytext-paired notebooks across all tracks ──────────────
PAIRED_NB_PY := $(shell find tracks -type f -name '*.py' 2>/dev/null | xargs grep -l 'formats: ipynb' 2>/dev/null)
INTRO        := tracks/01-intro
TEMPORAL     := tracks/02-temporal
CLAI_AGENT   := $(INTRO)/examples/cli_agent.yaml
CLAUDE_AGENT := $(INTRO)/examples/clai_anthropic.yaml
TEMPORAL_COMPOSE := docker compose -f $(TEMPORAL)/docker/docker-compose.yml
CAPSTONE_COMPOSE := docker compose -f $(TEMPORAL)/examples/11_capstone_fastapi/docker-compose.yml

help:  ## Show this list of targets
	@awk 'BEGIN { FS = ":.*##"; printf "\nUsage: make <target>\n\nTargets:\n" } \
	      /^[a-zA-Z_%-]+:.*##/ { printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2 }' \
	      $(MAKEFILE_LIST)
	@printf "\nPer-lesson runners:\n"
	@printf "  \033[36mintro-NN\033[0m            Run an intro-track lesson, e.g. \`make intro-04\`\n"
	@printf "  \033[36mtemporal-NN\033[0m         Run a temporal-track lesson's starter (worker must be up)\n"
	@printf "  \033[36mtemporal-NN-worker\033[0m  Run a temporal-track lesson's worker in the foreground\n\n"

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

# ── temporal track ─────────────────────────────────────────────────────────
# Pattern targets:
#   make temporal-NN-worker  -> uv run python tracks/02-temporal/examples/NN_*/worker.py
#   make temporal-NN         -> uv run python tracks/02-temporal/examples/NN_*/example.py
# Each lesson is its own subdirectory: a co-located README.md plus the lesson's
# code. The worker/starter file split is a study-loop convention, not a
# Temporal requirement — see tracks/02-temporal/README.md.

temporal-%-worker:
	@dir=$$(ls -d $(TEMPORAL)/examples/$**/ 2>/dev/null | head -1); \
	if [ -z "$$dir" ]; then \
		echo "$(TEMPORAL)/examples/ — no lesson $* yet. See $(TEMPORAL)/README.md"; exit 1; \
	elif [ -f "$$dir/worker.py" ]; then \
		uv run --env-file .env python "$$dir/worker.py"; \
	else \
		echo "$$dir has no worker.py"; exit 1; \
	fi

temporal-%:
	@dir=$$(ls -d $(TEMPORAL)/examples/$**/ 2>/dev/null | head -1); \
	if [ -z "$$dir" ]; then \
		echo "$(TEMPORAL)/examples/ — no lesson $* yet. See $(TEMPORAL)/README.md"; exit 1; \
	fi; \
	pynb=""; \
	for f in $$dir*.py; do \
		[ -f "$$f" ] && head -3 "$$f" 2>/dev/null | grep -q "jupyter:" && pynb="$$f" && break; \
	done; \
	if [ -n "$$pynb" ]; then \
		echo "Temporal lesson $* is a paired notebook ($${pynb%.py}.ipynb)."; \
		echo "Open in VS Code or run: make nb-exec"; \
	elif [ -f "$$dir/example.py" ]; then \
		uv run --env-file .env python "$$dir/example.py"; \
	elif [ -f "$$dir/starter.py" ]; then \
		uv run --env-file .env python "$$dir/starter.py"; \
	elif [ -f "$$dir/app.py" ]; then \
		uv run --env-file .env uvicorn --app-dir "$$dir" app:app --port 8001 --reload; \
	else \
		echo "$(TEMPORAL)/examples/ — no lesson $* yet. See $(TEMPORAL)/README.md"; exit 1; \
	fi

# ── temporal: self-hosted server (docker-compose) ──────────────────────────
temporal-up:  ## Start the self-hosted Temporal stack (postgres + server + UI)
	$(TEMPORAL_COMPOSE) up -d
	@echo ""
	@echo "Temporal UI:    http://localhost:8080"
	@echo "Frontend gRPC:  localhost:7233"
	@echo "Namespace:      learn-pydantic-ai"

temporal-down:  ## Stop the Temporal stack (keeps the postgres volume — data survives)
	$(TEMPORAL_COMPOSE) down

temporal-clean:  ## Stop AND wipe the postgres volume (fresh slate next boot)
	$(TEMPORAL_COMPOSE) down -v

temporal-ui:  ## Open the Temporal UI in your default browser
	@open http://localhost:8080 2>/dev/null || xdg-open http://localhost:8080 2>/dev/null || echo "Open http://localhost:8080 manually"

temporal-status:  ## Check the local Temporal cluster's health
	@temporal --address localhost:7233 operator cluster health 2>/dev/null \
	  || echo "temporal CLI cannot reach localhost:7233 — is `make temporal-up` running?"

# ── lesson 10 capstone: full self-contained stack (Temporal + worker + FastAPI) ─
temporal-11-up:  ## Bring up the capstone stack (Temporal + worker + FastAPI). Reads GOOGLE_API_KEY from your env / .env
	@set -a; [ -f .env ] && . ./.env; set +a; $(CAPSTONE_COMPOSE) up -d --build
	@echo ""
	@echo "FastAPI docs:   http://localhost:8001/docs"
	@echo "Temporal UI:    http://localhost:8080"
	@echo "Try:            make temporal-11-curl"

temporal-11-build:  ## Rebuild the capstone worker + API image (after code changes)
	@set -a; [ -f .env ] && . ./.env; set +a; $(CAPSTONE_COMPOSE) build

temporal-11-down:  ## Stop the capstone stack (keeps the postgres volume)
	@set -a; [ -f .env ] && . ./.env; set +a; $(CAPSTONE_COMPOSE) down

temporal-11-clean:  ## Stop + wipe the capstone postgres volume (fresh slate)
	@set -a; [ -f .env ] && . ./.env; set +a; $(CAPSTONE_COMPOSE) down -v

temporal-11-logs:  ## Tail logs from the capstone worker + API containers
	@set -a; [ -f .env ] && . ./.env; set +a; $(CAPSTONE_COMPOSE) logs -f worker api

temporal-11-api:  ## Run JUST the FastAPI app locally (worker must be up via temporal-11-worker)
	uv run --env-file .env uvicorn \
	  --app-dir $(TEMPORAL)/examples/11_capstone_fastapi app:app \
	  --port 8001 --reload

temporal-11-curl:  ## Drive the capstone end-to-end via curl (server must be up)
	@bash $(TEMPORAL)/examples/11_capstone_fastapi/demo.sh

temporal-11-ui:  ## Streamlit frontend for the capstone (worker + temporal-11-api must be up)
	uv run --env-file .env streamlit run \
	  $(TEMPORAL)/examples/11_capstone_fastapi/ui.py \
	  --server.port 8501 --server.headless true

# ── tests ──────────────────────────────────────────────────────────────────
test:  ## Run the intro Lesson 10 test file (fast, mocked)
	uv run pytest $(INTRO)/examples/10_testing.py -v

test-all:  ## Discover and run every test under tracks/*/examples (fast, mocked)
	uv run pytest tracks/*/examples/ -v

test-lessons:  ## Live smoke test — every intro lesson via `make intro-NN` (hits real APIs)
	uv run pytest $(INTRO)/tests/test_lessons.py -v

test-clai:  ## Live smoke test — both YAML-defined clai agents incl. Anthropic native tools
	uv run pytest $(INTRO)/tests/test_clai_agents.py -v

test-lessons-temporal:  ## Smoke test — every temporal lesson under WorkflowEnvironment.start_local()
	uv run --env-file .env pytest $(TEMPORAL)/tests/ -v --ignore=$(TEMPORAL)/tests/test_against_local_server.py

test-against-local-server:  ## Smoke test against your docker-compose server (requires `make temporal-up` first)
	uv run --env-file .env pytest $(TEMPORAL)/tests/test_against_local_server.py -v

test-live: test-lessons test-clai test-lessons-temporal  ## Every live test (intro lessons + clai + temporal lessons)

# ── model lookup ───────────────────────────────────────────────────────────
dump-models:  ## Regenerate data/models.json (lookup table of valid provider:model strings)
	uv run python scripts/dump_models.py

# ── housekeeping ───────────────────────────────────────────────────────────
clean:  ## Remove caches and build cruft
	rm -rf .pytest_cache tracks/*/examples/__pycache__ tracks/*/examples/.ipynb_checkpoints
