"""Shared test infrastructure.

These tests hit real LLM APIs and cost money. They are deliberately NOT
collected by `make test` / `make test-all`. Run via:

    make test-lessons   # every lesson via `make lesson-NN`
    make test-clai      # both YAML-defined agents
    make test-live      # both of the above
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def run(cmd: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    """Run a command from the repo root with combined stdout/stderr."""
    return subprocess.run(
        cmd,
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@pytest.fixture(autouse=True, scope="session")
def _require_make():
    if shutil.which("make") is None:
        pytest.skip("make not installed; live test suite requires it")


@pytest.fixture(autouse=True, scope="session")
def _require_env():
    env_file = REPO / ".env"
    if not env_file.exists():
        pytest.skip(".env missing; live tests need real API keys")
