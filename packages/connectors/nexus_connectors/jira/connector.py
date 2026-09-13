from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from nexus_sdk import Connector, ConnectorError


class JiraConnector(Connector):
    manifest_path = Path(__file__).parent / "manifest.yaml"

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.credentials.get("base_url", "").rstrip("/"),
            auth=(self.credentials.get("email", ""), self.credentials.get("api_token", "")),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30,
        )

    async def _get(self, path: str) -> dict[str, Any]:
        async with self._client() as c:
            resp = await c.get(path)
        if not resp.is_success:
            raise ConnectorError(f"Jira {resp.status_code}: {resp.text}", retriable=resp.status_code >= 500)
        return resp.json()

    async def _post(self, path: str, body: dict) -> dict[str, Any]:
        async with self._client() as c:
            resp = await c.post(path, json=body)
        if not resp.is_success:
            raise ConnectorError(f"Jira {resp.status_code}: {resp.text}", retriable=resp.status_code >= 500)
        return resp.json() if resp.content else {}

    async def _put(self, path: str, body: dict) -> None:
        async with self._client() as c:
            resp = await c.put(path, json=body)
        if not resp.is_success:
            raise ConnectorError(f"Jira {resp.status_code}: {resp.text}", retriable=resp.status_code >= 500)

    async def test_connection(self) -> dict[str, Any]:
        data = await self._get("/rest/api/3/myself")
        return {"ok": True, "account_id": data.get("accountId"), "email": data.get("emailAddress")}

    async def execute_action(self, action_key: str, inputs: dict[str, Any]) -> dict[str, Any]:
        return await self._dispatch(action_key, inputs)

    async def action_create_issue(self, inputs: dict[str, Any]) -> dict[str, Any]:
        fields: dict[str, Any] = {
            "project": {"key": inputs["project_key"]},
            "summary": inputs["summary"],
            "issuetype": {"name": inputs.get("issue_type", "Task")},
        }
        if desc := inputs.get("description"):
            fields["description"] = {"type": "doc", "version": 1, "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": desc}]}
            ]}
        if prio := inputs.get("priority"):
            fields["priority"] = {"name": prio}
        if assignee := inputs.get("assignee_account_id"):
            fields["assignee"] = {"accountId": assignee}
        if labels_raw := inputs.get("labels"):
            fields["labels"] = [l.strip() for l in labels_raw.split(",") if l.strip()]

        data = await self._post("/rest/api/3/issue", {"fields": fields})
        base = self.credentials.get("base_url", "").rstrip("/")
        return {
            "issue_key": data.get("key"),
            "issue_id": data.get("id"),
            "url": f"{base}/browse/{data.get('key')}",
        }

    async def action_update_issue(self, inputs: dict[str, Any]) -> dict[str, Any]:
        issue_key = inputs["issue_key"]
        fields: dict[str, Any] = {}
        if summary := inputs.get("summary"):
            fields["summary"] = summary
        if desc := inputs.get("description"):
            fields["description"] = {"type": "doc", "version": 1, "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": desc}]}
            ]}
        if assignee := inputs.get("assignee_account_id"):
            fields["assignee"] = {"accountId": assignee}
        await self._put(f"/rest/api/3/issue/{issue_key}", {"fields": fields})
        return {"issue_key": issue_key}

    async def action_transition_issue(self, inputs: dict[str, Any]) -> dict[str, Any]:
        issue_key = inputs["issue_key"]
        async with self._client() as c:
            resp = await c.post(
                f"/rest/api/3/issue/{issue_key}/transitions",
                json={"transition": {"id": inputs["transition_id"]}},
            )
        if not resp.is_success:
            raise ConnectorError(f"Transition failed {resp.status_code}: {resp.text}", retriable=False)
        return {"ok": True}

    async def action_add_comment(self, inputs: dict[str, Any]) -> dict[str, Any]:
        issue_key = inputs["issue_key"]
        body = {"body": {"type": "doc", "version": 1, "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": inputs["body"]}]}
        ]}}
        data = await self._post(f"/rest/api/3/issue/{issue_key}/comment", body)
        return {"comment_id": data.get("id", "")}

    async def action_get_issue(self, inputs: dict[str, Any]) -> dict[str, Any]:
        data = await self._get(f"/rest/api/3/issue/{inputs['issue_key']}")
        fields = data.get("fields", {})
        return {
            "issue_key": data.get("key"),
            "summary": fields.get("summary"),
            "status": fields.get("status", {}).get("name"),
            "assignee": (fields.get("assignee") or {}).get("displayName"),
        }
