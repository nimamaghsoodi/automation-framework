"""
Connector registry endpoints — list installed connectors and their manifests.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.connector import Connector
from app.worker.connector_registry import all_keys

router = APIRouter(prefix="/connectors", tags=["connectors"])


@router.get("/")
async def list_connectors(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Connector).order_by(Connector.name))
    return [
        {
            "id": str(c.id),
            "key": c.key,
            "name": c.name,
            "category": c.category,
            "manifest_version": c.manifest_version,
            "icon_url": c.icon_url,
            "description": c.description,
        }
        for c in rows.scalars()
    ]


@router.get("/{connector_key}")
async def get_connector(connector_key: str, db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Connector).where(Connector.key == connector_key))
    c = rows.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Connector not found")
    return {
        "id": str(c.id),
        "key": c.key,
        "name": c.name,
        "category": c.category,
        "manifest_version": c.manifest_version,
        "icon_url": c.icon_url,
        "description": c.description,
    }
