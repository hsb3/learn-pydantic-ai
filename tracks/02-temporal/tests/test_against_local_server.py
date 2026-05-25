"""Integration test: the FastAPI HTTP layer against running servers.

`test_lesson_11.py` drives `CapstoneWorkflow` in-process under
`WorkflowEnvironment.start_local()` — it never touches `app.py`. This test
covers the gap: it launches the *real* deployable processes — the capstone
worker and a uvicorn-served FastAPI app — against your running Temporal
stack, then exercises the HTTP contract end-to-end:

    POST /research  ->  poll GET /research/{id}  ->  POST .../approve  ->  GET (completed)

Run it via `make test-against-local-server` (requires `make temporal-up`).
It is skipped automatically when no Temporal server is reachable on
localhost:7233, and the docker-free suite (`make test-lessons-temporal`)
ignores this file entirely.
"""

from __future__ import annotations

import asyncio
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest
from temporalio.client import Client

TRACK = Path(__file__).resolve().parents[1]
LESSON_DIR = TRACK / "lessons" / "11_capstone_fastapi"
WORKER_PY = LESSON_DIR / "worker.py"

ADDRESS = "localhost:7233"
NAMESPACE = "learn-pydantic-ai"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _tail(path: str, n: int = 40) -> str:
    try:
        return "\n".join(Path(path).read_text().splitlines()[-n:])
    except OSError:
        return "(no log)"


async def _server_reachable() -> bool:
    try:
        await asyncio.wait_for(Client.connect(ADDRESS, namespace=NAMESPACE), timeout=5)
        return True
    except Exception:
        return False


async def _await_health(
    http: httpx.AsyncClient, base: str, dump: Callable[[], str], timeout: float = 30
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if (await http.get(f"{base}/healthz")).status_code == 200:
                return
        except httpx.TransportError:
            pass  # uvicorn not listening yet
        await asyncio.sleep(0.5)
    pytest.fail("FastAPI app never became healthy\n" + dump())


async def _poll_status(
    http: httpx.AsyncClient,
    base: str,
    wf_id: str,
    *,
    want: str,
    timeout: float,
    dump: Callable[[], str],
) -> None:
    deadline = time.monotonic() + timeout
    last = "?"
    while time.monotonic() < deadline:
        r = await http.get(f"{base}/research/{wf_id}")
        if r.status_code == 200:
            last = r.json()["status"]
            if last == want:
                return
        await asyncio.sleep(1)
    pytest.fail(f"workflow {wf_id} never reached {want!r} (last={last!r})\n" + dump())


@pytest.mark.asyncio
async def test_capstone_http_endpoints_against_running_servers() -> None:
    """POST/GET/approve over real HTTP against a live worker + uvicorn + Temporal."""
    if not await _server_reachable():
        pytest.skip(f"no Temporal server at {ADDRESS} — run `make temporal-up` first")

    port = _free_port()
    base = f"http://127.0.0.1:{port}"

    worker_log = tempfile.NamedTemporaryFile("w+", suffix="-worker.log", delete=False)
    api_log = tempfile.NamedTemporaryFile("w+", suffix="-api.log", delete=False)

    def _dump() -> str:
        worker_log.flush()
        api_log.flush()
        return (
            f"--- worker.log ({worker_log.name}) ---\n{_tail(worker_log.name)}\n"
            f"--- api.log ({api_log.name}) ---\n{_tail(api_log.name)}"
        )

    # Real deployable processes. Running the .py files puts the lesson dir on
    # sys.path[0] so their `from workflow import ...` / `app:app` imports
    # resolve. Both connect to the default localhost:7233 / learn-pydantic-ai
    # stack via `connect()`; subprocesses inherit API keys from this process's
    # env (the Make target runs pytest with `--env-file .env`).
    worker = subprocess.Popen(
        [sys.executable, str(WORKER_PY)],
        stdout=worker_log,
        stderr=subprocess.STDOUT,
    )
    api = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app:app",
            "--app-dir",
            str(LESSON_DIR),
            "--port",
            str(port),
        ],
        stdout=api_log,
        stderr=subprocess.STDOUT,
    )

    try:
        async with httpx.AsyncClient(timeout=30) as http:
            # 1. Wait for uvicorn to come up.
            await _await_health(http, base, _dump)

            # 2. Start a research workflow over HTTP.
            r = await http.post(
                f"{base}/research", json={"topic": "the population of Japan"}
            )
            assert r.status_code == 200, r.text
            wf_id = r.json()["workflow_id"]
            assert wf_id.startswith("research-")

            # 3. Poll until the workflow reaches the HITL gate. Generous budget:
            #    pre-fetch activity + three chained model calls.
            await _poll_status(
                http, base, wf_id, want="awaiting_approval", timeout=150, dump=_dump
            )

            # 4. The draft should be readable before approval.
            gate = (await http.get(f"{base}/research/{wf_id}")).json()
            assert gate["draft"], "expected a draft to be exposed before approval"

            # 5. Approve via the HTTP endpoint.
            a = await http.post(
                f"{base}/research/{wf_id}/approve", json={"note": "looks good"}
            )
            assert a.status_code == 200, a.text
            assert a.json()["status"] == "approved"

            # 6. Poll until completed; the final report must carry the note.
            await _poll_status(
                http, base, wf_id, want="completed", timeout=60, dump=_dump
            )
            final = (await http.get(f"{base}/research/{wf_id}")).json()
            assert final["status"] == "completed"
            assert final["final_report"]
            assert "looks good" in final["final_report"]

            # 7. Approving an unknown workflow exercises the 404 error path.
            nf = await http.post(
                f"{base}/research/does-not-exist/approve", json={"note": "x"}
            )
            assert nf.status_code == 404
    finally:
        for p in (api, worker):
            p.terminate()
        for p in (api, worker):
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
