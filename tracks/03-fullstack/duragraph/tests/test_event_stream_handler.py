"""Verifies event_stream_handler maps pydantic-ai stream events to the right
langgraph stream_mode envelopes. Re-run after any pydantic-ai upgrade — this
is the guard against the version-drift risk in the streaming seam.

    OPENAI_API_KEY=sk-test python -m pytest tests/        # or just run this file
"""
from __future__ import annotations

import asyncio
import dataclasses as dc
import os
from dataclasses import MISSING

os.environ.setdefault("OPENAI_API_KEY", "sk-test-not-used")  # construction only; no network

import pydantic_ai.messages as M  # noqa: E402

import worker.agents as A  # noqa: E402


def _build(cls, **vals):
    """Construct a dataclass event, filling any required field we didn't set."""
    kw = dict(vals)
    for f in dc.fields(cls):
        if f.name in kw or f.default is not MISSING or f.default_factory is not MISSING:
            continue
        kw[f.name] = "x"
    return cls(**kw)


def _run_handler(events):
    captured: list[tuple[str, dict]] = []

    async def fake_publish(run_id, event, data):
        captured.append((event, data))

    A.publish_event = fake_publish  # patch the name bound inside agents.py

    class Ctx:
        deps = A.Deps(run_id="r1")

    async def gen():
        for e in events:
            yield e

    asyncio.run(A.event_stream_handler(Ctx(), gen()))
    return captured


def test_event_stream_handler_mapping():
    events = [
        _build(M.PartStartEvent, index=0, part=_build(M.TextPart, content="Hel")),
        _build(M.PartDeltaEvent, index=0, delta=_build(M.TextPartDelta, content_delta="lo")),
        _build(M.PartDeltaEvent, index=1, delta=_build(M.ThinkingPartDelta, content_delta="hmm")),
        _build(M.FunctionToolCallEvent,
               part=_build(M.ToolCallPart, tool_name="get_weather", args='{"city":"NYC"}', tool_call_id="t1")),
        _build(M.FunctionToolResultEvent,
               part=_build(M.ToolReturnPart, tool_name="get_weather", content="sunny", tool_call_id="t1"),
               content="sunny"),
        _build(M.FinalResultEvent, tool_name="final_result"),
    ]
    captured = _run_handler(events)
    modes = [e for e, _ in captured]

    # assistant tokens -> messages, reassembling in order
    assert "".join(d["delta"] for e, d in captured if e == "messages") == "Hello"
    assert modes.count("messages") == 2
    # thinking + final_result -> events
    assert any(e == "events" and d["type"] == "thinking" for e, d in captured)
    assert any(e == "events" and d["type"] == "final_result" for e, d in captured)
    # tool lifecycle -> updates
    assert any(e == "updates" and d["type"] == "tool_call" and d["tool"] == "get_weather" for e, d in captured)
    assert any(e == "updates" and d["type"] == "tool_result" for e, d in captured)


if __name__ == "__main__":
    test_event_stream_handler_mapping()
    print("ALL ASSERTIONS PASSED")
