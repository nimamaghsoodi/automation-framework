from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db import get_db
from app.models.credential import CredentialInstance
from app.models.user import User
from app.services.connector_sync import DEV_USER_ID
from app.services.credential_service import encrypt_credentials, decrypt_payload
from nexus_sdk.registry import get_connector_class
from nexus_sdk.connector import ConnectorError

router = APIRouter(prefix="/credentials", tags=["credentials"], dependencies=[Depends(get_current_user)])


class CredentialCreateRequest(BaseModel):
    connector_id: str
    name: str
    payload: dict[str, Any]


@router.get("/")
async def list_credentials(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(CredentialInstance).order_by(CredentialInstance.name))
    return [_serialize(c) for c in rows.scalars()]


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_credential(body: CredentialCreateRequest, db: AsyncSession = Depends(get_db)):
    cred = CredentialInstance(
        connector_id=uuid.UUID(body.connector_id),
        name=body.name,
        owner_id=DEV_USER_ID,
        encrypted_payload=encrypt_credentials(body.payload),
    )
    db.add(cred)
    await db.commit()
    await db.refresh(cred)
    return _serialize(cred)


@router.post("/{credential_id}/test")
async def test_credential(credential_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Decrypt the credential, instantiate the connector, and call test_connection()."""
    cred = await db.get(CredentialInstance, credential_id)
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")

    # Look up the connector key via the connector row
    from app.models.connector import Connector
    connector_row = await db.get(Connector, cred.connector_id)
    if not connector_row:
        raise HTTPException(status_code=404, detail="Connector not found for this credential")

    try:
        ConnectorClass = get_connector_class(connector_row.key)
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Connector {connector_row.key!r} not loaded in registry")

    credentials = decrypt_payload(cred.encrypted_payload)
    connector = ConnectorClass(credentials=credentials)

    try:
        result = await connector.test_connection()
        cred.status = "active"
    except ConnectorError as exc:
        cred.status = "invalid"
        result = {"ok": False, "error": str(exc)}

    cred.last_tested_at = datetime.now(timezone.utc)
    await db.commit()
    return result


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(credential_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    cred = await db.get(CredentialInstance, credential_id)
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    await db.delete(cred)
    await db.commit()


def _serialize(c: CredentialInstance) -> dict:
    return {
        "id": str(c.id),
        "connector_id": str(c.connector_id),
        "name": c.name,
        "status": c.status,
        "last_tested_at": c.last_tested_at.isoformat() if c.last_tested_at else None,
    }
