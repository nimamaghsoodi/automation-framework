"""
Sync registered connector manifests into the DB on startup.
Keeps the connectors table current with what's actually installed.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nexus_sdk.registry import all_manifests
from app.models.connector import Connector


async def sync_connectors(db: AsyncSession) -> None:
    manifests = all_manifests()
    for key, manifest in manifests.items():
        result = await db.execute(select(Connector).where(Connector.key == key))
        row = result.scalar_one_or_none()
        if row is None:
            db.add(Connector(
                key=key,
                name=manifest.get("name", key),
                category=manifest.get("category", "generic"),
                manifest_version=manifest.get("version", "1.0.0"),
                icon_url=manifest.get("icon_url"),
                description=manifest.get("description"),
            ))
        else:
            row.name = manifest.get("name", key)
            row.category = manifest.get("category", "generic")
            row.manifest_version = manifest.get("version", "1.0.0")
            row.icon_url = manifest.get("icon_url")
            row.description = manifest.get("description")
    await db.commit()
