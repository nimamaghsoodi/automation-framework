from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from nexus_sdk import Connector, ConnectorError

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class TeamsConnector(Connector):
    manifest_path = Path(__file__).parent / "manifest.yaml"

    async def _get_token(self) -> str:
        if token := self.credentials.get("access_token"):
            return token
        tenant = self.credentials.get("tenant_id", "")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.credentials.get("client_id", ""),
                    "client_secret": self.credentials.get("client_secret", ""),
                    "scope": "https://graph.microsoft.com/.default",
                },
            )
        if not resp.is_success:
            raise ConnectorError(f"Token request failed: {resp.text}", retriable=False)
        return resp.json()["access_token"]

    async def _graph(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method,
                f"{GRAPH_BASE}{path}",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                **kwargs,
            )
        if not resp.is_success:
            raise ConnectorError(f"Graph API error {resp.status_code}: {resp.text}", retriable=resp.status_code >= 500)
        return resp.json() if resp.content else {}

    async def test_connection(self) -> dict[str, Any]:
        await self._get_token()
        return {"ok": True}

    async def execute_action(self, action_key: str, inputs: dict[str, Any]) -> dict[str, Any]:
        return await self._dispatch(action_key, inputs)

    async def action_send_channel_message(self, inputs: dict[str, Any]) -> dict[str, Any]:
        team_id = inputs["team_id"]
        channel_id = inputs["channel_id"]
        result = await self._graph(
            "POST",
            f"/teams/{team_id}/channels/{channel_id}/messages",
            json={"body": {"contentType": "html", "content": inputs["message"]}},
        )
        return {"message_id": result.get("id"), "created_at": result.get("createdDateTime")}

    async def action_send_chat_message(self, inputs: dict[str, Any]) -> dict[str, Any]:
        result = await self._graph(
            "POST",
            f"/chats/{inputs['chat_id']}/messages",
            json={"body": {"content": inputs["message"]}},
        )
        return {"message_id": result.get("id")}

    async def action_create_meeting(self, inputs: dict[str, Any]) -> dict[str, Any]:
        result = await self._graph(
            "POST",
            "/me/onlineMeetings",
            json={
                "subject": inputs["subject"],
                "startDateTime": inputs["start_datetime"],
                "endDateTime": inputs["end_datetime"],
            },
        )
        return {
            "meeting_id": result.get("id"),
            "join_url": result.get("joinUrl"),
            "join_web_url": result.get("joinWebUrl"),
        }
