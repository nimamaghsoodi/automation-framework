"""
ExecutionBackend interface — the execution engine is always accessed through
this abstraction so the Celery backend can be swapped for Temporal (or
another durable executor) without touching the rest of the codebase.
"""
from __future__ import annotations

import abc
import uuid
from typing import Any


class ExecutionBackend(abc.ABC):

    @abc.abstractmethod
    async def submit_run(
        self,
        run_id: uuid.UUID,
        flow_id: uuid.UUID,
        graph_snapshot: dict[str, Any],
        trigger_payload: dict[str, Any],
    ) -> str:
        """
        Enqueue execution of a flow run.
        Returns a backend-specific task ID (stored on the Run row for status polling).
        """

    @abc.abstractmethod
    async def get_status(self, task_id: str) -> dict[str, Any]:
        """
        Return current task status from the backend.
        Shape: {"state": "PENDING|STARTED|SUCCESS|FAILURE|REVOKED", "result": ..., "traceback": ...}
        """

    @abc.abstractmethod
    async def cancel(self, task_id: str) -> None:
        """Request cancellation of a running task."""
