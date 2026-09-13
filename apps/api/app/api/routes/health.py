from fastapi import APIRouter
from sqlalchemy import text
from app.db import AsyncSessionLocal

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness() -> dict:
    """Checks DB connectivity — used by k8s readiness probe."""
    async with AsyncSessionLocal() as db:
        await db.execute(text("SELECT 1"))
    return {"status": "ready"}
