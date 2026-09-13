"""
Credential vault CRUD.
Raw secrets are never returned after creation — only masked placeholders.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.credential import CredentialInstance
from app.services.credential_service import encrypt_credentials

router = APIRouter(prefix="/credentials", tags=["credentials"])


class CredentialCreateRequest(BaseModel):
    connector_id: str
    name: str
    payload: dict[str, Any]  # raw credential fields — encrypted immediately, never stored plain


class CredentialResponse(BaseModel):
    id: str
    connector_id: str
    name: str
    status: str
    last_tested_at: str | None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[CredentialResponse])
async def list_credentials(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(select(CredentialInstance).order_by(CredentialInstance.name))
    return [_serialize(c) for c in rows.scalars()]


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=CredentialResponse)
async def create_credential(body: CredentialCreateRequest, db: AsyncSession = Depends(get_db)):
    placeholder_owner = uuid.uuid4()  # replace with authenticated user
    cred = CredentialInstance(
        connector_id=uuid.UUID(body.connector_id),
        name=body.name,
        owner_id=placeholder_owner,
        encrypted_payload=encrypt_credentials(body.payload),
    )
    db.add(cred)
    await db.commit()
    await db.refresh(cred)
    return _serialize(cred)


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
