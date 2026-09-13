"""
Celery task: execute a flow run.

Walks the DAG in topological order, calls connector actions,
persists RunStep records, and publishes step-level status updates
to Redis pub/sub so the WebSocket endpoint can stream them to the UI.
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

import redis
from celery import Task

from app.celery_app import celery_app
from app.config import settings
from app.worker.dag import FlowContext, topological_sort
from nexus_sdk import get_connector_class
from app.services.credential_service import decrypt_credentials
from app.worker.connector_registry import autodiscover as _autodiscover

_autodiscover()  # register all connectors in worker process


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _publish(run_id: str, payload: dict) -> None:
    """Fire-and-forget publish to Redis pub/sub channel for this run."""
    try:
        r = redis.from_url(settings.redis_url)
        r.publish(f"run:{run_id}", json.dumps(payload))
        r.close()
    except Exception:
        pass  # observability failure must never break execution


@celery_app.task(
    name="nexus.execute_flow_run",
    bind=True,
    max_retries=0,
    acks_late=True,
)
def execute_flow_run(
    self: Task,
    run_id: str,
    flow_id: str,
    graph_snapshot: dict[str, Any],
    trigger_payload: dict[str, Any],
) -> dict[str, Any]:
    return asyncio.get_event_loop().run_until_complete(
        _execute(self, run_id, flow_id, graph_snapshot, trigger_payload)
    )


async def _execute(
    task: Task,
    run_id: str,
    flow_id: str,
    graph: dict[str, Any],
    trigger_payload: dict[str, Any],
) -> dict[str, Any]:
    from app.db import AsyncSessionLocal
    from app.models.run import Run, RunStep

    nodes_by_id = {n["id"]: n for n in graph["nodes"]}
    edges = graph["edges"]
    order = topological_sort(graph["nodes"], edges)

    predecessors: dict[str, list[str]] = {nid: [] for nid in nodes_by_id}
    for edge in edges:
        predecessors[edge["target"]].append(edge["source"])

    ctx = FlowContext(trigger_payload)

    async with AsyncSessionLocal() as db:
        run = await db.get(Run, uuid.UUID(run_id))
        if run is None:
            return {"error": "Run not found"}
        run.status = "running"
        await db.commit()

        _publish(run_id, {"event": "run_started", "run_status": "running"})

        run_failed = False

        for node_id in order:
            node = nodes_by_id[node_id]
            node_type = node.get("type")

            if node_type == "trigger":
                ctx.set_output(node_id, trigger_payload)
                _publish(run_id, {
                    "event": "step_update",
                    "node_id": node_id,
                    "step_status": "success",
                })
                continue

            inputs: dict[str, Any] = {}
            for pred_id in predecessors[node_id]:
                pred_out = ctx.get_output(pred_id) or {}
                inputs.update(pred_out)
            inputs.update(node.get("config_json", {}))

            try:
                node_uuid = uuid.UUID(node_id)
            except ValueError:
                node_uuid = uuid.uuid5(uuid.UUID(run_id), node_id)

            step = RunStep(
                run_id=uuid.UUID(run_id),
                node_id=node_uuid,
                status="running",
                input_json=inputs,
                attempt=1,
            )
            db.add(step)
            await db.flush()

            _publish(run_id, {"event": "step_update", "node_id": node_id, "step_status": "running"})

            t_start = time.monotonic()
            output: dict[str, Any] = {}
            error: str | None = None

            try:
                connector_key = node.get("connector_key")
                action_key = node.get("config_json", {}).get("action_key")

                if node_type == "action" and connector_key and action_key:
                    ConnectorClass = get_connector_class(connector_key)
                    cred_instance_id = node.get("config_json", {}).get("credential_instance_id")
                    credentials = await decrypt_credentials(db, cred_instance_id) if cred_instance_id else {}
                    connector = ConnectorClass(credentials=credentials)
                    output = await connector.execute_action(action_key, inputs)

                elif node_type == "condition":
                    expr = node.get("config_json", {}).get("expression", "true")
                    result = eval(expr, {"__builtins__": {}}, ctx.as_dict())  # noqa: S307
                    output = {"result": bool(result), "expression": expr}

                elif node_type == "transform":
                    mapping = node.get("config_json", {}).get("mapping", {})
                    output = {
                        k: eval(v, {"__builtins__": {}}, ctx.as_dict())  # noqa: S307
                        for k, v in mapping.items()
                    }

                step.status = "success"
                step.output_json = output
                ctx.set_output(node_id, output)

            except Exception as exc:
                run_failed = True
                error = str(exc)
                step.status = "failed"
                step.error = error

            finally:
                step.duration_ms = int((time.monotonic() - t_start) * 1000)
                step.finished_at = _now()
                await db.commit()

            _publish(run_id, {
                "event": "step_update",
                "node_id": node_id,
                "step_id": str(step.id),
                "step_status": step.status,
                "duration_ms": step.duration_ms,
                "error": error,
            })

            if run_failed:
                break

        run.status = "failed" if run_failed else "success"
        run.finished_at = _now()
        await db.commit()

    _publish(run_id, {"event": "run_finished", "run_status": run.status})
    return {"run_id": run_id, "status": run.status}
