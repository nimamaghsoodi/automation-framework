"""
Schedule management — enable/disable cron scheduling for a flow.
Uses celery-redbeat to register dynamic periodic tasks in Redis.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from celery.schedules import crontab
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.celery_app import celery_app
from app.db import get_db
from app.models.flow import Flow

router = APIRouter(prefix="/schedules", tags=["schedules"], dependencies=[Depends(get_current_user)])

REDBEAT_KEY_PREFIX = "nexus-flow-"


def _parse_cron(expr: str) -> crontab:
    parts = expr.strip().split()
    if len(parts) != 5:
        raise ValueError("Cron expression must have exactly 5 fields: minute hour day month weekday")
    minute, hour, dom, month, dow = parts
    return crontab(minute=minute, hour=hour, day_of_month=dom, month_of_year=month, day_of_week=dow)


def _redbeat_key(flow_id: str) -> str:
    return f"{REDBEAT_KEY_PREFIX}{flow_id}"


class ScheduleRequest(BaseModel):
    cron_expression: str
    trigger_payload: dict[str, Any] = {}


class ScheduleResponse(BaseModel):
    flow_id: str
    cron_expression: str
    enabled: bool
    next_run: str | None = None


@router.put("/{flow_id}")
async def set_schedule(
    flow_id: uuid.UUID,
    body: ScheduleRequest,
    db: AsyncSession = Depends(get_db),
) -> ScheduleResponse:
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()
    if flow is None:
        raise HTTPException(404, "Flow not found")

    try:
        schedule = _parse_cron(body.cron_expression)
    except ValueError as e:
        raise HTTPException(422, str(e))

    # Persist cron expression in graph_json so the UI can read it back
    graph = dict(flow.graph_json)
    graph["cron_expression"] = body.cron_expression
    graph["cron_trigger_payload"] = body.trigger_payload
    flow.graph_json = graph
    flow.status = "active"
    await db.commit()

    # Register with redbeat
    try:
        from redbeat import RedBeatSchedulerEntry

        entry = RedBeatSchedulerEntry(
            name=_redbeat_key(str(flow_id)),
            task="nexus.execute_flow_run",
            schedule=schedule,
            kwargs={
                "flow_id": str(flow_id),
                "trigger_payload": {
                    "scheduled_at": datetime.now(timezone.utc).isoformat(),
                    "source": "cron",
                    **body.trigger_payload,
                },
            },
            app=celery_app,
        )
        entry.save()
    except Exception as exc:
        raise HTTPException(500, f"Failed to register schedule: {exc}")

    return ScheduleResponse(
        flow_id=str(flow_id),
        cron_expression=body.cron_expression,
        enabled=True,
    )


@router.delete("/{flow_id}", status_code=204)
async def delete_schedule(
    flow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()
    if flow is None:
        raise HTTPException(404, "Flow not found")

    # Remove from graph_json
    graph = dict(flow.graph_json)
    graph.pop("cron_expression", None)
    graph.pop("cron_trigger_payload", None)
    flow.graph_json = graph
    flow.status = "paused"
    await db.commit()

    # Remove from redbeat
    try:
        from redbeat import RedBeatSchedulerEntry

        entry = RedBeatSchedulerEntry.from_key(
            f"redbeat:{_redbeat_key(str(flow_id))}", app=celery_app
        )
        entry.delete()
    except Exception:
        pass  # already gone or never existed


@router.get("/{flow_id}")
async def get_schedule(
    flow_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ScheduleResponse:
    result = await db.execute(select(Flow).where(Flow.id == flow_id))
    flow = result.scalar_one_or_none()
    if flow is None:
        raise HTTPException(404, "Flow not found")

    cron_expr = flow.graph_json.get("cron_expression")
    return ScheduleResponse(
        flow_id=str(flow_id),
        cron_expression=cron_expr or "",
        enabled=bool(cron_expr and flow.status == "active"),
    )
