"""Shared helpers for the examples.

Loads .env so GOOGLE_API_KEY is available to the `google:` provider.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

FLASH = "google:gemini-3-flash-preview"
PRO = "google:gemini-3-pro-preview"
