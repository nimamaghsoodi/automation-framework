from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, flows, runs, connectors, credentials, schedules
from app.api.routes import auth as auth_router
from app.api.routes import users as users_router
from app.api.routes.ws import router as ws_router
from app.db import AsyncSessionLocal
from app.services.connector_sync import sync_connectors, seed_dev_user, seed_admin_user
from app.worker.connector_registry import autodiscover


@asynccontextmanager
async def lifespan(app: FastAPI):
    autodiscover()
    async with AsyncSessionLocal() as db:
        await seed_dev_user(db)
        await seed_admin_user(db)
        await sync_connectors(db)
    yield


app = FastAPI(
    title="Nexus Automation Framework",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Public routes (no auth required)
app.include_router(health.router)
app.include_router(auth_router.router, prefix="/api/v1")

# Protected routes
app.include_router(flows.router, prefix="/api/v1")
app.include_router(runs.router, prefix="/api/v1")
app.include_router(connectors.router, prefix="/api/v1")
app.include_router(credentials.router, prefix="/api/v1")
app.include_router(schedules.router, prefix="/api/v1")
app.include_router(users_router.router, prefix="/api/v1")
app.include_router(ws_router)
