"""AG-UI runtime for an agent — the worked example behind `runtimes.md`.

`Agent.to_ag_ui()` is gone. The replacement is `AGUIAdapter.dispatch_request`,
which you call from your own route: you own the app, the adapter owns one
request/response.

Runs keyless — `TestModel` answers instead of a provider, so this is the one
runtime example you can drive without an API key:

    make ag-ui                      # serve on :8002
    uv run python docs/ag_ui_app.py --check   # in-process self-check, no server

Swap `TestModel()` for `MODELS["google"]["fast"]` to point it at a real model.
"""

from __future__ import annotations

import json
import sys

from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel
from pydantic_ai.ui.ag_ui import AGUIAdapter
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

agent = Agent(TestModel())


@agent.tool_plain
def get_weather(city: str) -> str:
    """Look up the weather. A tool call is what makes the AG-UI stream interesting."""
    return f"It's foggy in {city}."


async def run_agent(request: Request) -> Response:
    """One route, one line: hand the request to the adapter with the agent to run.

    `dispatch_request` parses the AG-UI `RunAgentInput` body, runs the agent, and
    returns a streaming `text/event-stream` response of AG-UI events.
    """
    return await AGUIAdapter.dispatch_request(request, agent=agent)


app = Starlette(routes=[Route("/", run_agent, methods=["POST"])])


# --- self-check ------------------------------------------------------------
# `--check` drives `app` in-process and asserts the event envelope, so the
# wiring above stays honest without a server, a port, or an API key.

RUN_INPUT = {
    "threadId": "thread-1",
    "runId": "run-1",
    "state": {},
    "messages": [{"id": "m1", "role": "user", "content": "What's the weather in SF?"}],
    "tools": [],
    "context": [],
    "forwardedProps": {},
}


async def _check() -> None:
    import httpx

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/", json=RUN_INPUT, headers={"accept": "text/event-stream"}
        )
        r.raise_for_status()
        body = r.text

    events = [
        line.removeprefix("data: ")
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    kinds = [json.loads(e)["type"] for e in events]
    print("\n".join(kinds))

    assert kinds[0] == "RUN_STARTED", kinds[:1]
    assert kinds[-1] == "RUN_FINISHED", kinds[-1:]
    for expected in ("TOOL_CALL_START", "TOOL_CALL_END", "TEXT_MESSAGE_CONTENT"):
        assert expected in kinds, f"missing {expected} in {kinds}"
    print("\nOK — RUN_STARTED … RUN_FINISHED, with a tool call and streamed text.")


if __name__ == "__main__":
    if "--check" in sys.argv:
        import asyncio

        asyncio.run(_check())
    else:
        import uvicorn

        uvicorn.run(app, host="127.0.0.1", port=8002)
