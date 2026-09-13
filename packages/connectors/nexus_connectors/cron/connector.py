from __future__ import annotations

from pathlib import Path
from typing import Any

from nexus_sdk import Connector, ConnectorError


class CronConnector(Connector):
    manifest_path = Path(__file__).parent / "manifest.yaml"

    async def test_connection(self) -> dict[str, Any]:
        return {"ok": True}

    async def execute_action(self, action_key: str, inputs: dict[str, Any]) -> dict[str, Any]:
        raise ConnectorError("Cron is a trigger-only connector and has no actions.")
