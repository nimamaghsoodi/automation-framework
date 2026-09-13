from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from nexus_sdk import Connector, ConnectorError


class HttpRestConnector(Connector):
    manifest_path = Path(__file__).parent / "manifest.yaml"

    def _build_auth_headers(self) -> dict[str, str]:
        creds = self.credentials
        auth_type = creds.get("auth_type", "none")
        if auth_type == "api_key":
            header = creds.get("api_key_header", "X-Api-Key")
            return {header: creds.get("api_key", "")}
        if auth_type == "bearer":
            return {"Authorization": f"Bearer {creds.get('api_key', '')}"}
        return {}

    def _build_httpx_auth(self) -> httpx.BasicAuth | None:
        creds = self.credentials
        if creds.get("auth_type") == "basic":
            return httpx.BasicAuth(creds.get("username", ""), creds.get("password", ""))
        return None

    async def test_connection(self) -> dict[str, Any]:
        return {"ok": True}

    async def execute_action(self, action_key: str, inputs: dict[str, Any]) -> dict[str, Any]:
        if action_key != "request":
            raise ConnectorError(f"Unknown action: {action_key!r}")
        return await self.action_request(inputs)

    async def action_request(self, inputs: dict[str, Any]) -> dict[str, Any]:
        url = inputs.get("url")
        if not url:
            raise ConnectorError("'url' is required")

        method = inputs.get("method", "GET").upper()
        extra_headers = inputs.get("headers", {})
        query_params = inputs.get("query_params", {})
        body = inputs.get("body", {})
        timeout = inputs.get("timeout_seconds", 30)
        follow_redirects = inputs.get("follow_redirects", True)

        auth_headers = self._build_auth_headers()
        auth = self._build_httpx_auth()

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=follow_redirects,
            auth=auth,
        ) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers={**auth_headers, **extra_headers},
                    params=query_params,
                    json=body if body else None,
                )
            except httpx.TimeoutException:
                raise ConnectorError(f"Request timed out after {timeout}s", retriable=True)
            except httpx.RequestError as exc:
                raise ConnectorError(str(exc), retriable=True)

        try:
            resp_body = response.json()
        except Exception:
            resp_body = {"_raw": response.text}

        return {
            "status_code": response.status_code,
            "ok": response.is_success,
            "body": resp_body,
            "headers": dict(response.headers),
        }
