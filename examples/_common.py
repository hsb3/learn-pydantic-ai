"""Shared helpers for the examples.

Loads `.env` so the provider modules can pick up their API keys.

Exposes `MODELS` — a {provider: {tier: model_string}} dict with two tiers
("fast" and "smart") per provider — and validates each entry against the
committed `data/models.json` catalog at import time so a typo fails fast.

`FLASH` / `PRO` remain as Google-tier aliases so Lessons 02-12 keep
working unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


# Two presets per provider — pick the right tier per task instead of
# hard-coding strings throughout the lessons.
MODELS: dict[str, dict[str, str]] = {
    "anthropic": {
        "fast": "anthropic:claude-haiku-4-5",
        "smart": "anthropic:claude-sonnet-4-6",
    },
    "google": {
        "fast": "google:gemini-3-flash-preview",
        "smart": "google:gemini-3-pro-preview",
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
        # Catalog is committed; only missing if someone deleted it.
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
            "examples/_common.py model presets out of sync with "
            "data/models.json:\n"
            f"{details}\n"
            "Either fix the strings, or run `make dump-models` after "
            "upgrading pydantic-ai."
        )


_validate_presets()
