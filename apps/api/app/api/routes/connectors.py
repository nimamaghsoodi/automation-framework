from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db import get_db
from app.models.connector import Connector
from nexus_sdk.registry import get_manifest, all_manifests

router = APIRouter(prefix="/connectors", tags=["connectors"], dependencies=[Depends(get_current_user)])


@router.get("/")
async def list_connectors(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Connector).order_by(Connector.name))
    return [_serialize(c) for c in rows.scalars()]


@router.get("/{connector_key}/manifest")
async def get_connector_manifest(connector_key: str):
    """Returns the full manifest JSON for a connector — used by the UI to render dynamic forms."""
    manifest = get_manifest(connector_key)
    if manifest is None:
        raise HTTPException(status_code=404, detail=f"No manifest found for connector: {connector_key!r}")
    return manifest


@router.get("/manifests/all")
async def list_all_manifests():
    """Returns all registered connector manifests in one call — used to populate the connector palette."""
    return all_manifests()


@router.get("/{connector_key}")
async def get_connector(connector_key: str, db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(Connector).where(Connector.key == connector_key))
    c = rows.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Connector not found")
    return _serialize(c)


def _serialize(c: Connector) -> dict:
    return {
        "id": str(c.id),
        "key": c.key,
        "name": c.name,
        "category": c.category,
        "manifest_version": c.manifest_version,
        "icon_url": c.icon_url,
        "description": c.description,
    }
