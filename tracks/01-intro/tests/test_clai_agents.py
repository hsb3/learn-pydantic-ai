"""End-to-end tests for the two YAML-defined clai agents.

- tracks/01-intro/examples/cli_agent.yaml         Google Gemini, WebSearch + light Thinking
- tracks/01-intro/examples/clai_anthropic.yaml    Claude Sonnet 4.6, WebSearch + code_execution

The Anthropic-side tests double as confirmation that pydantic-ai is
setting the `anthropic-beta` headers correctly for the native tools.
A 400 / unknown-tool error would surface here.
"""

from __future__ import annotations

import pytest

from conftest import run


def _pai(agent: str, prompt: str, timeout: int = 120):
    return run(
        [
            "uv",
            "run",
            "--env-file",
            ".env",
            "pai",
            "--agent",
            agent,
            "--no-stream",
            prompt,
        ],
        timeout=timeout,
    )


# ── Gemini agent (cli_agent.yaml) ──────────────────────────────────────────


def test_cli_agent_responds() -> None:
    r = _pai("tracks/01-intro/examples/cli_agent.yaml", "What is 2 + 2? One word answer.")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "4" in r.stdout or "four" in r.stdout.lower(), (
        f"unexpected output:\n{r.stdout}"
    )


def test_cli_agent_uses_web_search() -> None:
    r = _pai(
        "tracks/01-intro/examples/cli_agent.yaml",
        "Use web search to find the current year. Reply with just the 4-digit year.",
        timeout=180,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    # year should appear in output
    assert any(str(y) in r.stdout for y in range(2024, 2030))


# ── Claude agent (clai_anthropic.yaml) ─────────────────────────────────────


def test_claude_agent_responds() -> None:
    r = _pai("tracks/01-intro/examples/clai_anthropic.yaml", "What is 2 + 2? One word answer.")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "4" in r.stdout or "four" in r.stdout.lower()


def test_claude_native_web_search() -> None:
    """Exercise Anthropic's native web_search — proves beta headers work."""
    r = _pai(
        "tracks/01-intro/examples/clai_anthropic.yaml",
        "Use web search to find what year it is. Reply with just the year.",
        timeout=180,
    )
    assert r.returncode == 0, (
        "Anthropic web_search failed — beta-header / model-access issue?\n"
        f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    )
    assert any(str(y) in r.stdout for y in range(2024, 2030))


def test_claude_native_code_execution() -> None:
    """Exercise Anthropic's native code_execution — proves beta headers work."""
    r = _pai(
        "tracks/01-intro/examples/clai_anthropic.yaml",
        "Use code execution to compute 17! / (12! * 5!). Reply with just the integer.",
        timeout=180,
    )
    assert r.returncode == 0, (
        "Anthropic code_execution failed — beta-header / model-access issue?\n"
        f"stdout:\n{r.stdout}\nstderr:\n{r.stderr}"
    )
    # 17! / (12! * 5!) = 6188 — C(17, 5)
    assert "6188" in r.stdout, f"unexpected output:\n{r.stdout}"
