from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import health, flows, runs, connectors, credentials
from app.worker.connector_registry import autodiscover


@asynccontextmanager
async def lifespan(app: FastAPI):
    autodiscover()  # scan nexus_connectors package so all connectors register
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
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(flows.router, prefix="/api/v1")
app.include_router(runs.router, prefix="/api/v1")
app.include_router(connectors.router, prefix="/api/v1")
app.include_router(credentials.router, prefix="/api/v1")
