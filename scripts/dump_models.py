"""Dump valid pydantic-ai model strings to data/models.json for lookup / validation.

Source of truth is `pydantic_ai.models.KnownModelName` — the same Literal
type the library uses internally and that `pai -l` reads from. Re-run
this any time you bump `pydantic-ai`:

    make dump-models
    # or
    uv run python scripts/dump_models.py

Output:

    data/models.json
        {
          "generated_at": "...",
          "pydantic_ai_version": "...",
          "providers": {
            "anthropic": [...],
            "google":    [...],
            "openai":    [...],         # Responses API
            "openai-chat": [...],       # Chat Completions API
          },
          "all_kept": [...],
          "counts": {...},
          "other_providers_skipped": [...]  # bedrock, cohere, mistral, ...
        }
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import get_args

import pydantic_ai
from pydantic_ai.models import KnownModelName

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "models.json"

# Providers we care about for this project. Drop / extend as needed.
KEEP_PROVIDERS: tuple[str, ...] = ("anthropic", "google", "openai", "openai-chat")


def main() -> int:
    # KnownModelName is a TypeAliasType (PEP 695); the underlying Literal
    # is on .__value__. get_args() returns every string in the Literal.
    all_models: list[str] = sorted(get_args(KnownModelName.__value__))

    by_provider: dict[str, list[str]] = {p: [] for p in KEEP_PROVIDERS}
    other_provider_names: set[str] = set()

    for m in all_models:
        prefix = m.split(":", 1)[0]
        if prefix in by_provider:
            by_provider[prefix].append(m)
        else:
            other_provider_names.add(prefix)

    kept_flat = sorted({m for models in by_provider.values() for m in models})

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pydantic_ai_version": pydantic_ai.__version__,
        "providers": by_provider,
        "all_kept": kept_flat,
        "counts": {p: len(by_provider[p]) for p in KEEP_PROVIDERS},
        "other_providers_skipped": sorted(other_provider_names),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2) + "\n")

    total = sum(out["counts"].values())
    print(
        f"Wrote {OUT.relative_to(REPO)} — {total} models across {len(KEEP_PROVIDERS)} providers "
        f"(pydantic-ai {pydantic_ai.__version__})"
    )
    for prov, count in out["counts"].items():
        print(f"  {prov:14} {count:4}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
