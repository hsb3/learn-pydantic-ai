from fastapi import APIRouter, Depends
from app.deps import get_gateway
from app.schemas import Assistant, AssistantCreate
from app.services.temporal_gateway import TemporalGateway

router = APIRouter(prefix="/assistants", tags=["assistants"])


@router.post("", response_model=Assistant)
async def create_assistant(body: AssistantCreate, gw: TemporalGateway = Depends(get_gateway)):
    return gw.create_assistant(body.name, body.agent, body.config)


@router.get("/{assistant_id}", response_model=Assistant)
async def get_assistant(assistant_id: str, gw: TemporalGateway = Depends(get_gateway)):
    return gw.get_assistant(assistant_id)
