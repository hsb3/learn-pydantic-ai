"""Shared test infrastructure for the Temporal track.

Tests run against `WorkflowEnvironment.start_local()` — an in-process,
ephemeral Temporal server bundled with the `temporalio` SDK. No docker
required to run the suite.

Path-resolution mirrors `tracks/01-intro/tests/conftest.py`.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# tests/ -> tracks/02-temporal/ -> tracks/ -> repo root
REPO = Path(__file__).resolve().parents[3]
TRACK = Path(__file__).resolve().parents[1]  # tracks/02-temporal/
LESSONS = TRACK / "lessons"


def use_lesson(slug: str, *, extra_dirs: tuple[str, ...] = ()) -> Path:
    """Make the lesson dir's modules importable as plain names.

    Each lesson dir contains a `workflows.py` / `workflow.py` that the
    Makefile runs as `python <dir>/worker.py`, putting that dir on
    `sys.path[0]` so `from workflows import X` resolves to the local
    file. Pytest doesn't reproduce that automatically when several test
    modules in one process each want their own `workflows`.

    IMPORTANT: call this at BOTH module-level AND at the start of each
    test function. Module-level handles the test's own `from workflows
    import X`. The in-function call re-pins sys.path right before the
    Worker validates the workflow — by then, other test modules' own
    `use_lesson()` calls may have re-ordered sys.path, leaving the
    Temporal sandbox looking at the wrong sibling's file.

    `extra_dirs` is for tests (like Lesson 11's FastAPI capstone) that
    need a SECOND lesson's dir on `sys.path` too.

    Returns the lesson dir path.
    """
    target = LESSONS / slug
    extras = [LESSONS / d for d in extra_dirs]
    # Evict every sibling lesson's dir from sys.path so a stale entry
    # can't shadow the one we want.
    for d in LESSONS.iterdir():
        if not d.is_dir() or d == target or d in extras:
            continue
        while str(d) in sys.path:
            sys.path.remove(str(d))
    # Drop cached modules that any sibling lesson might have registered
    # under the same name. This includes:
    #   - top-level lesson files (workflows.py / workflow.py / app.py / etc.)
    #   - sub-packages (agents.*, activities) that lessons 10 and 11 both
    #     define under the same names — without eviction, cached
    #     `agents.researcher` from one lesson silently shadows the other.
    # Iterate by prefix to catch every submodule.
    _EVICT_PREFIXES = (
        "workflows",
        "workflow",
        "scraper",
        "flaky_tool",
        "schemas",
        "app",
        "agents",
        "activities",
    )
    for cached_name in list(sys.modules):
        if any(
            cached_name == p or cached_name.startswith(p + ".") for p in _EVICT_PREFIXES
        ):
            sys.modules.pop(cached_name, None)
    # Push target + extras to the front, target last so it ends up at index 0.
    for d in extras:
        s = str(d)
        while s in sys.path:
            sys.path.remove(s)
        sys.path.insert(0, s)
    s = str(target)
    while s in sys.path:
        sys.path.remove(s)
    sys.path.insert(0, s)
    return target


def run(cmd: list[str], timeout: int = 180) -> subprocess.CompletedProcess[str]:
    """Run a command from the repo root with combined stdout/stderr captured."""
    return subprocess.run(
        cmd,
        cwd=REPO,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


@pytest.fixture(autouse=True, scope="session")
def _require_make() -> None:
    if shutil.which("make") is None:
        pytest.skip("make not installed; live test suite requires it")


@pytest.fixture(autouse=True, scope="session")
def _require_env() -> None:
    env_file = REPO / ".env"
    if not env_file.exists():
        pytest.skip(".env missing; live tests need real API keys")
