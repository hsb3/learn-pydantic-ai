from fastapi import APIRouter, Depends
from app.deps import get_gateway
from app.schemas import Thread, ThreadCreate, ThreadState
from app.services.temporal_gateway import TemporalGateway

router = APIRouter(prefix="/threads", tags=["threads"])


@router.post("", response_model=Thread)
async def create_thread(body: ThreadCreate, gw: TemporalGateway = Depends(get_gateway)):
    return await gw.create_thread(body.metadata)


@router.get("/{thread_id}/state", response_model=ThreadState)
async def get_state(thread_id: str, gw: TemporalGateway = Depends(get_gateway)):
    return await gw.get_state(thread_id)


@router.get("/{thread_id}/history")
async def get_history(thread_id: str, gw: TemporalGateway = Depends(get_gateway)):
    return await gw.get_history(thread_id)
