from __future__ import annotations

import uuid
from typing import Any

from app.execution.backend import ExecutionBackend
from app.celery_app import celery_app


class CeleryExecutionBackend(ExecutionBackend):

    async def submit_run(
        self,
        run_id: uuid.UUID,
        flow_id: uuid.UUID,
        graph_snapshot: dict[str, Any],
        trigger_payload: dict[str, Any],
    ) -> str:
        task = celery_app.send_task(
            "nexus.execute_flow_run",
            kwargs={
                "run_id": str(run_id),
                "flow_id": str(flow_id),
                "graph_snapshot": graph_snapshot,
                "trigger_payload": trigger_payload,
            },
        )
        return task.id

    async def get_status(self, task_id: str) -> dict[str, Any]:
        result = celery_app.AsyncResult(task_id)
        return {
            "state": result.state,
            "result": result.result if result.ready() else None,
            "traceback": result.traceback,
        }

    async def cancel(self, task_id: str) -> None:
        celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
