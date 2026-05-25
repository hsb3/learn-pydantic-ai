"""Wire contract. Field names deliberately mirror langgraph-api so existing
clients (and the langgraph_sdk shape) feel familiar.

langgraph-api parallels noted inline. We intentionally implement a SUBSET:
threads, runs (background + stream), state, history, cancel, resume. That is
~80% of the surface you actually use day to day.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ---- assistants (langgraph: a graph + config + version) ----
class AssistantCreate(BaseModel):
    name: str
    agent: str = Field(description="Registered Pydantic AI agent key (see worker/agents.py)")
    config: dict[str, Any] = Field(default_factory=dict)


class Assistant(BaseModel):
    assistant_id: str
    name: str
    agent: str
    config: dict[str, Any]
    created_at: datetime


# ---- threads ----
class ThreadCreate(BaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)


class Thread(BaseModel):
    thread_id: str
    status: Literal["idle", "busy", "interrupted"]
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ThreadState(BaseModel):
    """langgraph: GET /threads/{id}/state — current durable state of the thread."""
    thread_id: str
    values: dict[str, Any]                 # e.g. {"messages": [...]}
    interrupts: list[Interrupt] = Field(default_factory=list)
    next: list[str] = Field(default_factory=list)


class Interrupt(BaseModel):
    run_id: str
    value: Any                              # what the agent is asking the human


# ---- runs ----
class RunStatus(str, Enum):
    pending = "pending"
    running = "running"
    interrupted = "interrupted"   # langgraph HITL: waiting on human input
    success = "success"
    error = "error"
    cancelled = "cancelled"


class Command(BaseModel):
    """langgraph: resume an interrupted run by POSTing a run with a Command."""
    resume: Any | None = None


class RunCreate(BaseModel):
    assistant_id: str
    input: dict[str, Any] | None = None     # e.g. {"messages": [{"role": "user", "content": "..."}]}
    command: Command | None = None          # provide instead of `input` to resume an interrupt
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    # langgraph stream_mode: values | messages | updates | events.
    # We map all of these onto one Redis event stream and tag each event.
    stream_mode: list[str] = Field(default_factory=lambda: ["values"])


class Run(BaseModel):
    run_id: str
    thread_id: str
    assistant_id: str
    status: RunStatus
    created_at: datetime


# ---- streaming envelope (one shape for every SSE event) ----
class StreamEvent(BaseModel):
    """Emitted over SSE. `event` mirrors langgraph stream_mode names so the
    client switch statement is unchanged: values | messages | updates |
    events | interrupt | end | error."""
    event: str
    run_id: str
    data: Any
