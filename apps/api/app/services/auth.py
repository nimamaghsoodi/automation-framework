from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
from jose import jwt

from app.config import settings


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: uuid.UUID, email: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "email": email, "role": role, "exp": expire},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict:
    """Raises jose.JWTError on invalid or expired token."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
