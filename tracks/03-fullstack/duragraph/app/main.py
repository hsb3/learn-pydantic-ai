"""Composition root: wire Temporal client + gateway, mount routes, register
the single error envelope. Auth (your NGINX/authorizer + JWT) belongs in a
dependency here — left as the one TODO that is genuinely yours."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.errors import DomainError, domain_error_handler
from app.routes import assistants, runs, threads
from app.services.temporal_gateway import TemporalGateway
from worker.client import build_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = await build_client()
    app.state.gateway = TemporalGateway(client)
    yield


app = FastAPI(title="duragraph", version="0.1.0", lifespan=lifespan)
app.add_exception_handler(DomainError, domain_error_handler)
app.include_router(assistants.router)
app.include_router(threads.router)
app.include_router(runs.router)


@app.get("/health")
async def health():
    return {"ok": True}
