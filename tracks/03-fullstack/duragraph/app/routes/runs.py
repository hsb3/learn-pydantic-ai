"""Runs — the heart of the contract. Background, streaming, status, cancel.
Resume is a run with `command.resume` set (langgraph semantics)."""
from uuid import uuid4

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.deps import get_gateway
from app.schemas import Run, RunCreate
from app.services.streaming import iter_events, open_subscription
from app.services.temporal_gateway import TemporalGateway

router = APIRouter(prefix="/threads/{thread_id}/runs", tags=["runs"])


@router.post("", response_model=Run)
async def create_run(thread_id: str, body: RunCreate, gw: TemporalGateway = Depends(get_gateway)):
    """langgraph: POST /threads/{id}/runs — fire-and-forget background run."""
    return await gw.create_run(thread_id, body)


@router.post("/stream")
async def stream_run(thread_id: str, body: RunCreate, gw: TemporalGateway = Depends(get_gateway)):
    """langgraph: POST /threads/{id}/runs/stream — SSE. Subscribe first, then signal."""
    run_id = f"run_{uuid4().hex}"
    r, ps = await open_subscription(run_id)            # live before we signal
    await gw.create_run(thread_id, body, run_id=run_id)
    return EventSourceResponse(iter_events(r, ps, run_id))


@router.get("/{run_id}", response_model=Run)
async def get_run(thread_id: str, run_id: str, gw: TemporalGateway = Depends(get_gateway)):
    return await gw.get_run(thread_id, run_id)


@router.post("/{run_id}/cancel")
async def cancel_run(thread_id: str, run_id: str, gw: TemporalGateway = Depends(get_gateway)):
    await gw.cancel_run(thread_id, run_id)
    return {"status": "cancelled"}
