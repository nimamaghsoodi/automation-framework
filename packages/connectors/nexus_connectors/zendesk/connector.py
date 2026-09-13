from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import httpx

from nexus_sdk import Connector, ConnectorError


class ZendeskConnector(Connector):
    manifest_path = Path(__file__).parent / "manifest.yaml"

    def _base_url(self) -> str:
        subdomain = self.credentials.get("subdomain", "")
        if not subdomain:
            raise ConnectorError(
                "Zendesk subdomain is not configured. Add a Zendesk credential with your subdomain (the part before .zendesk.com).",
                retriable=False,
            )
        return f"https://{subdomain}.zendesk.com/api/v2"

    def _auth_header(self) -> str:
        email = self.credentials.get("email", "")
        token = self.credentials.get("api_token", "")
        encoded = base64.b64encode(f"{email}/token:{token}".encode()).decode()
        return f"Basic {encoded}"

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.request(
                method,
                f"{self._base_url()}{path}",
                headers={"Authorization": self._auth_header(), "Content-Type": "application/json"},
                **kwargs,
            )
        if not resp.is_success:
            raise ConnectorError(
                f"Zendesk API {resp.status_code}: {resp.text}",
                retriable=resp.status_code >= 500,
            )
        return resp.json() if resp.content else {}

    async def test_connection(self) -> dict[str, Any]:
        data = await self._request("GET", "/users/me.json")
        return {"ok": True, "email": data.get("user", {}).get("email")}

    async def execute_action(self, action_key: str, inputs: dict[str, Any]) -> dict[str, Any]:
        return await self._dispatch(action_key, inputs)

    async def action_create_ticket(self, inputs: dict[str, Any]) -> dict[str, Any]:
        ticket: dict[str, Any] = {
            "subject": inputs["subject"],
            "comment": {"body": inputs["body"]},
            "priority": inputs.get("priority", "normal"),
        }
        if email := inputs.get("requester_email"):
            ticket["requester"] = {"email": email}
        if tags_raw := inputs.get("tags"):
            ticket["tags"] = [t.strip() for t in tags_raw.split(",") if t.strip()]

        data = await self._request("POST", "/tickets.json", json={"ticket": ticket})
        t = data.get("ticket", {})
        return {"ticket_id": str(t.get("id")), "url": t.get("url"), "status": t.get("status")}

    async def action_update_ticket(self, inputs: dict[str, Any]) -> dict[str, Any]:
        ticket_id = inputs["ticket_id"]
        update: dict[str, Any] = {}
        for field in ("status", "priority", "assignee_id"):
            if val := inputs.get(field):
                update[field] = val
        data = await self._request("PUT", f"/tickets/{ticket_id}.json", json={"ticket": update})
        t = data.get("ticket", {})
        return {"ticket_id": str(t.get("id")), "status": t.get("status")}

    async def action_add_comment(self, inputs: dict[str, Any]) -> dict[str, Any]:
        ticket_id = inputs["ticket_id"]
        data = await self._request(
            "PUT",
            f"/tickets/{ticket_id}.json",
            json={"ticket": {"comment": {"body": inputs["body"], "public": inputs.get("public", True)}}},
        )
        comment = data.get("audit", {}).get("events", [{}])[0]
        return {"comment_id": str(comment.get("id", ""))}

    async def action_get_ticket(self, inputs: dict[str, Any]) -> dict[str, Any]:
        data = await self._request("GET", f"/tickets/{inputs['ticket_id']}.json")
        t = data.get("ticket", {})
        return {
            "ticket_id": str(t.get("id")),
            "subject": t.get("subject"),
            "status": t.get("status"),
            "priority": t.get("priority"),
        }
