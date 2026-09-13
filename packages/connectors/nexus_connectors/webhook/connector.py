from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

from nexus_sdk import Connector, ConnectorError


class WebhookConnector(Connector):
    manifest_path = Path(__file__).parent / "manifest.yaml"

    async def test_connection(self) -> dict[str, Any]:
        return {"ok": True}

    async def execute_action(self, action_key: str, inputs: dict[str, Any]) -> dict[str, Any]:
        raise ConnectorError("Webhook connector has no actions — it is trigger-only.")

    async def handle_trigger(self, trigger_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        if trigger_key != "inbound":
            raise ConnectorError(f"Unknown trigger: {trigger_key!r}")
        return payload

    @staticmethod
    def verify_signature(signing_secret: str, body: bytes, signature_header: str) -> bool:
        """
        Verify HMAC-SHA256 signature from the X-Nexus-Signature header.
        Expected format: "sha256=<hex_digest>"
        """
        if not signature_header.startswith("sha256="):
            return False
        expected = hmac.new(signing_secret.encode(), body, hashlib.sha256).hexdigest()
        received = signature_header[len("sha256="):]
        return hmac.compare_digest(expected, received)
