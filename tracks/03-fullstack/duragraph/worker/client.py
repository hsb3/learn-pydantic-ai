"""Temporal client builder. PydanticAIPlugin is what makes TemporalAgent work
across the client/worker boundary. In prod, point at your private :7233
frontend and add TLS / API-key auth here.
"""
from __future__ import annotations

from pydantic_ai.durable_exec.temporal import PydanticAIPlugin
from temporalio.client import Client

from app.core.config import get_settings


async def build_client() -> Client:
    s = get_settings()
    return await Client.connect(
        s.temporal_address,
        namespace=s.temporal_namespace,
        plugins=[PydanticAIPlugin()],
    )
