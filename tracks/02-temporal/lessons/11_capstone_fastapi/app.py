"""Lesson 11 capstone — FastAPI front-end for the durable research workflow.

Three endpoints mirror the langgraph-api shape:

    POST /research                       -> start a workflow, return id
    GET  /research/{workflow_id}         -> poll status, draft, final report
    POST /research/{workflow_id}/approve -> send the HITL approval signal

Run locally: `make temporal-11-api` (worker must be up via
`make temporal-11-worker`).

Run in docker: `make temporal-11-up` brings up Temporal + worker + this
service together.
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException
from temporalio.client import WorkflowExecutionStatus, WorkflowQueryFailedError
from temporalio.service import RPCError

from learn_pydantic_ai import TASK_QUEUE, connect
from schemas import (
    ApprovalPayload,
    RejectPayload,
    ResearchHandle,
    ResearchRequest,
    ResearchStatus,
    RevisePayload,
)
from workflow import CapstoneWorkflow

app = FastAPI(title="learn-pydantic-ai capstone API")


@app.post("/research", response_model=ResearchHandle)
async def start_research(req: ResearchRequest) -> ResearchHandle:
    """Kick off a durable research workflow. Returns immediately with an id."""
    client = await connect()
    wf_id = f"research-{uuid.uuid4().hex[:8]}"
    await client.start_workflow(
        CapstoneWorkflow.run,
        req.topic,
        id=wf_id,
        task_queue=TASK_QUEUE,
    )
    return ResearchHandle(workflow_id=wf_id)


@app.get("/research/{workflow_id}", response_model=ResearchStatus)
async def get_research(workflow_id: str) -> ResearchStatus:
    """Return current state. If completed, includes the final report."""
    client = await connect()
    handle = client.get_workflow_handle(workflow_id)
    desc = await handle.describe()
    if desc.status == WorkflowExecutionStatus.COMPLETED:
        result = await handle.result()
        return ResearchStatus(
            workflow_id=workflow_id, status="completed", final_report=result
        )
    # Catch the narrow case where the workflow has started but hasn't
    # processed its first task yet (queries fail). Other RPC failures
    # propagate so we don't silently mask real bugs.
    try:
        live_status = await handle.query(CapstoneWorkflow.status)
        live_draft = await handle.query(CapstoneWorkflow.draft)
    except (WorkflowQueryFailedError, RPCError):
        live_status = "running"
        live_draft = ""
    return ResearchStatus(
        workflow_id=workflow_id,
        status=live_status,
        draft=live_draft or None,
    )


@app.post("/research/{workflow_id}/approve")
async def approve_research(
    workflow_id: str, payload: ApprovalPayload
) -> dict[str, str]:
    """Release the HITL gate. Workflow completes shortly after."""
    client = await connect()
    handle = client.get_workflow_handle(workflow_id)
    try:
        await handle.signal(CapstoneWorkflow.approve, payload.note)
    except RPCError as e:
        raise HTTPException(
            status_code=404, detail=f"workflow not found: {workflow_id}"
        ) from e
    return {"workflow_id": workflow_id, "status": "approved"}


@app.post("/research/{workflow_id}/revise")
async def revise_research(workflow_id: str, payload: RevisePayload) -> dict[str, str]:
    """Send the draft back to the writer with feedback; it returns to the gate."""
    client = await connect()
    handle = client.get_workflow_handle(workflow_id)
    try:
        await handle.signal(CapstoneWorkflow.revise, payload.feedback)
    except RPCError as e:
        raise HTTPException(
            status_code=404, detail=f"workflow not found: {workflow_id}"
        ) from e
    return {"workflow_id": workflow_id, "status": "revision_requested"}


@app.post("/research/{workflow_id}/reject")
async def reject_research(workflow_id: str, payload: RejectPayload) -> dict[str, str]:
    """Reject the draft; the workflow ends without shipping."""
    client = await connect()
    handle = client.get_workflow_handle(workflow_id)
    try:
        await handle.signal(CapstoneWorkflow.reject, payload.reason)
    except RPCError as e:
        raise HTTPException(
            status_code=404, detail=f"workflow not found: {workflow_id}"
        ) from e
    return {"workflow_id": workflow_id, "status": "rejected"}


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness check for the docker stack."""
    return {"status": "ok"}
