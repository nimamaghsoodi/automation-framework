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
from app.models.user import User

# Fixed dev user — created at startup when no auth middleware is wired yet
DEV_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def seed_dev_user(db: AsyncSession) -> None:
    result = await db.execute(select(User).where(User.id == DEV_USER_ID))
    if result.scalar_one_or_none() is None:
        db.add(User(
            id=DEV_USER_ID,
            email="dev@nexus.local",
            role="admin",
            is_active=True,
        ))
        await db.commit()


async def seed_admin_user(db: AsyncSession) -> None:
    """Ensure a human admin account with login credentials exists."""
    from app.config import settings
    from app.services.auth import hash_password

    result = await db.execute(select(User).where(User.email == settings.admin_email))
    user = result.scalar_one_or_none()
    if user is None:
        db.add(User(
            email=settings.admin_email,
            hashed_password=hash_password(settings.admin_password),
            role="admin",
            is_active=True,
        ))
        await db.commit()


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
