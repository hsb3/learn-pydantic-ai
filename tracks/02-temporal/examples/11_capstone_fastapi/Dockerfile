# Capstone image — builds both the worker and the FastAPI service.
# The compose file overrides `command:` per service so the same image
# runs in two different roles.
#
# Build context is the repo root (compose handles this) so we can copy
# the `learn_pydantic_ai/` package + the capstone dir into one image.

FROM python:3.13-slim AS base

# `uv` is the project's package manager — copy the prebuilt binary from
# the official uv image (faster than pip-installing).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# System deps. `tini` is optional but gives clean signal handling so
# Ctrl-C / docker stop terminates the worker fast.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH

# Stage 1 — install dependencies in their own layer (cacheable).
COPY pyproject.toml uv.lock ./
COPY learn_pydantic_ai/ ./learn_pydantic_ai/
COPY data/ ./data/
RUN uv sync --frozen --no-dev --no-install-project \
    && uv sync --frozen --no-dev

# Stage 2 — copy capstone source. Done after deps so source edits
# don't bust the dep cache.
COPY tracks/02-temporal/examples/11_capstone_fastapi/ ./capstone/

# All commands run from the capstone dir so `from workflow import X`
# resolves to the local file (the same way `python worker.py` does).
WORKDIR /app/capstone

ENTRYPOINT ["/usr/bin/tini", "--"]

# Default to the worker; compose overrides for the API container.
CMD ["python", "worker.py"]
