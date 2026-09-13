"""
User management — admin only.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.db import get_db
from app.models.user import User
from app.services.auth import hash_password

router = APIRouter(prefix="/users", tags=["users"])


class UserOut(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    sso_subject: str | None
    created_at: str

    model_config = {"from_attributes": True}


class UserCreateRequest(BaseModel):
    email: str
    password: str
    role: str = "viewer"


class UserUpdateRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    password: str | None = None


@router.get("/", response_model=list[UserOut])
async def list_users(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = await db.execute(select(User).order_by(User.created_at))
    return [_out(u) for u in rows.scalars()]


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreateRequest,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if body.role not in ("admin", "editor", "viewer"):
        raise HTTPException(status_code=422, detail="role must be admin, editor, or viewer")
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _out(user)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdateRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.role is not None:
        if body.role not in ("admin", "editor", "viewer"):
            raise HTTPException(status_code=422, detail="role must be admin, editor, or viewer")
        # Prevent the last admin from losing their role
        if user.role == "admin" and body.role != "admin":
            admins = await db.execute(select(User).where(User.role == "admin", User.is_active == True))  # noqa: E712
            if len(admins.scalars().all()) <= 1:
                raise HTTPException(status_code=400, detail="Cannot demote the last active admin")
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.hashed_password = hash_password(body.password)
    await db.commit()
    await db.refresh(user)
    return _out(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return _out(user)


def _out(u: User) -> dict:
    return {
        "id": str(u.id),
        "email": u.email,
        "role": u.role,
        "is_active": u.is_active,
        "sso_subject": u.sso_subject,
        "created_at": u.created_at.isoformat(),
    }
