"""Run every lesson via `make intro-NN` and confirm exit code 0.

- Lessons 02-09, 11, 12 are scripts — `make intro-NN` runs them with `uv run python`.
- Lesson 10 IS pytest — `make intro-10` runs the test file.
- Lessons 01 and 13 are paired notebooks — `make intro-NN` only prints a
  pointer, so we execute them headless via `jupyter nbconvert`.
"""

from __future__ import annotations

import pytest

from conftest import TRACK, run

SCRIPT_LESSONS = ["02", "03", "04", "05", "06", "07", "08", "09", "11", "12"]
NOTEBOOK_LESSONS = ["01", "13"]


@pytest.mark.parametrize("lesson", SCRIPT_LESSONS)
def test_lesson_script_runs(lesson: str) -> None:
    """`make intro-NN` for script-style lessons."""
    r = run(["make", f"intro-{lesson}"], timeout=180)
    assert r.returncode == 0, (
        f"\n--- make intro-{lesson} failed (rc={r.returncode}) ---\n"
        f"stdout:\n{r.stdout[-2000:]}\n"
        f"stderr:\n{r.stderr[-2000:]}"
    )


def test_lesson_10_pytest() -> None:
    """Lesson 10's own test file passes when invoked via `make intro-10`."""
    r = run(["make", "intro-10"], timeout=60)
    assert r.returncode == 0, r.stdout + "\n" + r.stderr


@pytest.mark.parametrize("lesson", NOTEBOOK_LESSONS)
def test_lesson_notebook_runs(lesson: str) -> None:
    """Lessons 01 and 13 are notebooks — execute headless."""
    nb = next(TRACK.glob(f"examples/{lesson}_*.ipynb"))
    r = run(
        [
            "uv",
            "run",
            "jupyter",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            "--output",
            f"/tmp/lesson-{lesson}-test-run.ipynb",
            str(nb),
            "--ExecutePreprocessor.timeout=180",
        ],
        timeout=300,
    )
    assert r.returncode == 0, (
        f"\n--- notebook {nb.name} failed (rc={r.returncode}) ---\n"
        f"stdout:\n{r.stdout[-2000:]}\n"
        f"stderr:\n{r.stderr[-2000:]}"
    )
