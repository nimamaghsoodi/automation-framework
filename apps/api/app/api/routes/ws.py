"""
WebSocket endpoint for live run status.

Architecture:
  Celery worker  →  redis.publish("run:{run_id}", json)
  FastAPI WS     →  redis.asyncio subscribe("run:{run_id}") → forward to browser
"""
from __future__ import annotations

import json
import uuid

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.config import settings

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/runs/{run_id}")
async def run_status_ws(websocket: WebSocket, run_id: uuid.UUID):
    await websocket.accept()
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = r.pubsub()
    channel = f"run:{run_id}"
    await pubsub.subscribe(channel)

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            data = message["data"]
            await websocket.send_text(data)
            # Terminate stream when run reaches a terminal state
            try:
                payload = json.loads(data)
                if payload.get("run_status") in ("success", "failed", "cancelled"):
                    break
            except (json.JSONDecodeError, AttributeError):
                pass
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await r.aclose()
