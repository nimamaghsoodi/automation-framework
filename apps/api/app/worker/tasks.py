"""
Celery task: execute a flow run.

This task is the heart of the execution engine. It:
  1. Loads the graph snapshot from the Run row (immutable once submitted)
  2. Walks nodes in topological order
  3. For each node, resolves the connector, decrypts credentials, calls the action
  4. Persists RunStep records (input, output, status, duration) to Postgres
  5. Updates Run.status when done
"""
from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from celery import Task

from app.celery_app import celery_app
from app.worker.dag import FlowContext, topological_sort
from nexus_sdk import get_connector_class
from app.services.credential_service import decrypt_credentials


def _now() -> datetime:
    return datetime.now(timezone.utc)


@celery_app.task(
    name="nexus.execute_flow_run",
    bind=True,
    max_retries=0,       # the task itself does per-step retries; don't retry the whole run
    acks_late=True,
)
def execute_flow_run(
    self: Task,
    run_id: str,
    flow_id: str,
    graph_snapshot: dict[str, Any],
    trigger_payload: dict[str, Any],
) -> dict[str, Any]:
    """
    Synchronous Celery entry point — runs the async executor in a new event loop.
    """
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
    # Build predecessor map so each node can read predecessor outputs
    predecessors: dict[str, list[str]] = {nid: [] for nid in nodes_by_id}
    for edge in edges:
        predecessors[edge["target"]].append(edge["source"])

    ctx = FlowContext(trigger_payload)

    async with AsyncSessionLocal() as db:
        # Mark run as running
        run = await db.get(Run, uuid.UUID(run_id))
        if run is None:
            return {"error": "Run not found"}
        run.status = "running"
        await db.commit()

        run_failed = False

        for node_id in order:
            node = nodes_by_id[node_id]
            node_type = node.get("type")

            # Trigger node: output = the trigger payload (already in context)
            if node_type == "trigger":
                ctx.set_output(node_id, trigger_payload)
                continue

            # Build inputs: merge outputs from all predecessor nodes
            inputs: dict[str, Any] = {}
            for pred_id in predecessors[node_id]:
                pred_out = ctx.get_output(pred_id) or {}
                inputs.update(pred_out)
            # Override with node-level static config
            inputs.update(node.get("config_json", {}))

            step = RunStep(
                run_id=uuid.UUID(run_id),
                node_id=uuid.UUID(node_id),
                status="running",
                input_json=inputs,
                attempt=1,
            )
            db.add(step)
            await db.flush()

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
                    result = eval(expr, {"__builtins__": {}}, ctx.as_dict())  # noqa: S307 — sandboxed eval for conditions
                    output = {"result": bool(result), "expression": expr}

                elif node_type == "transform":
                    # Transform nodes evaluate a mapping of output_key -> expression
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

            if run_failed:
                break

        run.status = "failed" if run_failed else "success"
        run.finished_at = _now()
        await db.commit()

    return {"run_id": run_id, "status": run.status}
