"""
Credential encryption/decryption using Fernet (AES-128-CBC + HMAC-SHA256).
Credentials are encrypted on write and decrypted only inside worker processes
for the duration of a step — never logged, never returned to the frontend.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings


def _fernet() -> Fernet:
    return Fernet(settings.encryption_key.encode())


def encrypt_credentials(payload: dict[str, Any]) -> bytes:
    return _fernet().encrypt(json.dumps(payload).encode())


def decrypt_payload(encrypted: bytes) -> dict[str, Any]:
    return json.loads(_fernet().decrypt(encrypted).decode())


async def decrypt_credentials(db: AsyncSession, credential_instance_id: str) -> dict[str, Any]:
    from app.models.credential import CredentialInstance

    cred = await db.get(CredentialInstance, uuid.UUID(credential_instance_id))
    if cred is None:
        raise ValueError(f"CredentialInstance {credential_instance_id!r} not found")
    return decrypt_payload(cred.encrypted_payload)
