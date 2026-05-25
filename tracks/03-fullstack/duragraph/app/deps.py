from fastapi import Request
from app.services.temporal_gateway import TemporalGateway


def get_gateway(request: Request) -> TemporalGateway:
    return request.app.state.gateway
