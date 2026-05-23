"""Shared helpers for every track in this repo.

Importable from anywhere once the project is installed editable
(automatic on `uv sync`):

    from learn_pydantic_ai import MODELS, FLASH, PRO

Loads `.env` at import time so the provider modules can pick up their
API keys. Validates `MODELS` against the committed `data/models.json`
catalog — a typo or stale string fails immediately.
"""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv

# `Path(__file__).parents[1]` resolves to the source-tree root even when
# the package is installed editable — pip/uv leave a .pth file and the
# source location is what `__file__` reports.
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")


# Two presets per provider — pick the right tier per task instead of
# hard-coding strings throughout the lessons.
MODELS: dict[str, dict[str, str]] = {
    "anthropic": {
        "fast": "anthropic:claude-haiku-4-5",
        "smart": "anthropic:claude-sonnet-4-6",
    },
    "google": {
        "fast": "google:gemini-flash-lite-latest",
        "smart": "google:gemini-flash-latest",
    },
    "openai": {
        "fast": "openai:gpt-5-mini",
        "smart": "openai:gpt-5.4",
    },
}

# Google-tier aliases — backward-compat for Lessons 02-12.
FLASH: str = MODELS["google"]["fast"]
PRO: str = MODELS["google"]["smart"]


def _validate_presets() -> None:
    """Fail fast if any preset doesn't appear in data/models.json."""
    catalog_path = PROJECT_ROOT / "data" / "models.json"
    if not catalog_path.exists():
        raise FileNotFoundError(
            f"{catalog_path.relative_to(PROJECT_ROOT)} not found. "
            "Run `make dump-models` to regenerate it."
        )
    valid = set(json.loads(catalog_path.read_text())["all_kept"])
    bad = [
        (provider, tier, model)
        for provider, tiers in MODELS.items()
        for tier, model in tiers.items()
        if model not in valid
    ]
    if bad:
        details = "\n".join(f"  - MODELS[{p!r}][{t!r}] = {m!r}" for p, t, m in bad)
        raise ValueError(
            "learn_pydantic_ai.MODELS out of sync with data/models.json:\n"
            f"{details}\n"
            "Either fix the strings, or run `make dump-models` after "
            "upgrading pydantic-ai."
        )


_validate_presets()


__all__ = ["MODELS", "FLASH", "PRO", "PROJECT_ROOT"]
