"""
Run trigger + history endpoints.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.api.deps import get_current_user
from app.db import get_db
from app.execution.celery_backend import CeleryExecutionBackend
from app.models.flow import Flow
from app.models.run import Run, RunStep

router = APIRouter(prefix="/runs", tags=["runs"], dependencies=[Depends(get_current_user)])
_backend = CeleryExecutionBackend()


class TriggerRunRequest(BaseModel):
    flow_id: str
    trigger_payload: dict[str, Any] = {}


class RunStepResponse(BaseModel):
    id: str
    node_id: str
    status: str
    input_json: dict | None
    output_json: dict | None
    error: str | None
    duration_ms: int | None
    attempt: int

    model_config = {"from_attributes": True}


class RunResponse(BaseModel):
    id: str
    flow_id: str
    flow_name: str
    flow_version: int
    trigger_source: str
    status: str
    started_at: str
    finished_at: str | None
    steps: list[RunStepResponse] = []

    model_config = {"from_attributes": True}


@router.post("/", response_model=RunResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_run(body: TriggerRunRequest, db: AsyncSession = Depends(get_db)):
    flow = await db.get(Flow, uuid.UUID(body.flow_id))
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    run = Run(
        flow_id=flow.id,
        flow_version=flow.version,
        trigger_source="manual",
        graph_snapshot=flow.graph_json,
        status="pending",
    )
    db.add(run)
    await db.commit()
    await db.refresh(run)

    task_id = await _backend.submit_run(
        run_id=run.id,
        flow_id=flow.id,
        graph_snapshot=flow.graph_json,
        trigger_payload=body.trigger_payload,
    )
    run.celery_task_id = task_id
    await db.commit()

    result = await db.execute(
        select(Run).where(Run.id == run.id).options(selectinload(Run.steps))
    )
    run = result.scalar_one()
    return _serialize_run(run)


@router.get("/", response_model=list[RunResponse])
async def list_runs(flow_id: str | None = None, db: AsyncSession = Depends(get_db)):
    q = (
        select(Run)
        .options(selectinload(Run.steps), joinedload(Run.flow))
        .order_by(Run.started_at.desc())
        .limit(100)
    )
    if flow_id:
        q = q.where(Run.flow_id == uuid.UUID(flow_id))
    rows = await db.execute(q)
    return [_serialize_run(r) for r in rows.scalars()]


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Run).where(Run.id == run_id).options(selectinload(Run.steps), joinedload(Run.flow))
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return _serialize_run(run)


@router.post("/{run_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_run(run_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    run = await db.get(Run, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.celery_task_id:
        await _backend.cancel(run.celery_task_id)
    run.status = "cancelled"
    await db.commit()


def _serialize_run(run: Run) -> dict:
    steps = getattr(run, "steps", []) or []
    flow = getattr(run, "flow", None)
    return {
        "id": str(run.id),
        "flow_id": str(run.flow_id),
        "flow_name": flow.name if flow else str(run.flow_id)[:8],
        "flow_version": run.flow_version,
        "trigger_source": run.trigger_source,
        "status": run.status,
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "steps": [
            {
                "id": str(s.id),
                "node_id": str(s.node_id),
                "status": s.status,
                "input_json": s.input_json,
                "output_json": s.output_json,
                "error": s.error,
                "duration_ms": s.duration_ms,
                "attempt": s.attempt,
            }
            for s in steps
        ],
    }
