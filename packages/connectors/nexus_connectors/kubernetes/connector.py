from __future__ import annotations

import base64
import json
import ssl
from pathlib import Path
from typing import Any

import httpx

from nexus_sdk import Connector, ConnectorError


class KubernetesConnector(Connector):
    manifest_path = Path(__file__).parent / "manifest.yaml"

    def _client(self) -> httpx.AsyncClient:
        token = self.credentials.get("token", "")
        base_url = self.credentials.get("server_url", "").rstrip("/")
        ca_b64 = self.credentials.get("ca_cert_base64")

        if ca_b64:
            ca_bytes = base64.b64decode(ca_b64)
            ssl_ctx = ssl.create_default_context(cadata=ca_bytes.decode())
        else:
            ssl_ctx = False  # skip verification for dev

        return httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            verify=ssl_ctx,
            timeout=30,
        )

    async def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        async with self._client() as c:
            resp = await c.get(path, params=params)
        if not resp.is_success:
            raise ConnectorError(f"k8s {resp.status_code}: {resp.text}", retriable=resp.status_code >= 500)
        return resp.json()

    async def _patch(self, path: str, body: dict, content_type: str = "application/merge-patch+json") -> dict[str, Any]:
        async with self._client() as c:
            resp = await c.patch(path, content=json.dumps(body), headers={"Content-Type": content_type})
        if not resp.is_success:
            raise ConnectorError(f"k8s {resp.status_code}: {resp.text}", retriable=resp.status_code >= 500)
        return resp.json()

    async def test_connection(self) -> dict[str, Any]:
        data = await self._get("/api")
        return {"ok": True, "versions": data.get("versions", [])}

    async def execute_action(self, action_key: str, inputs: dict[str, Any]) -> dict[str, Any]:
        return await self._dispatch(action_key, inputs)

    async def action_get_pod_status(self, inputs: dict[str, Any]) -> dict[str, Any]:
        ns = inputs.get("namespace", "default")
        pod = inputs["pod_name"]
        data = await self._get(f"/api/v1/namespaces/{ns}/pods/{pod}")
        status = data.get("status", {})
        return {
            "phase": status.get("phase"),
            "conditions": status.get("conditions", []),
            "container_statuses": status.get("containerStatuses", []),
        }

    async def action_list_pods(self, inputs: dict[str, Any]) -> dict[str, Any]:
        ns = inputs.get("namespace", "default")
        params = {}
        if sel := inputs.get("label_selector"):
            params["labelSelector"] = sel
        data = await self._get(f"/api/v1/namespaces/{ns}/pods", params=params)
        return {
            "pods": [
                {
                    "name": item["metadata"]["name"],
                    "phase": item.get("status", {}).get("phase"),
                    "ready": all(c.get("ready") for c in item.get("status", {}).get("containerStatuses", [])),
                }
                for item in data.get("items", [])
            ]
        }

    async def action_scale_deployment(self, inputs: dict[str, Any]) -> dict[str, Any]:
        ns = inputs.get("namespace", "default")
        name = inputs["deployment_name"]
        replicas = int(inputs["replicas"])
        await self._patch(
            f"/apis/apps/v1/namespaces/{ns}/deployments/{name}",
            {"spec": {"replicas": replicas}},
        )
        return {"deployment_name": name, "replicas": replicas}

    async def action_apply_manifest(self, inputs: dict[str, Any]) -> dict[str, Any]:
        manifest = inputs["manifest"]
        field_manager = inputs.get("field_manager", "nexus")
        api_version = manifest.get("apiVersion", "v1")
        kind = manifest.get("kind", "")
        name = manifest.get("metadata", {}).get("name", "")
        ns = manifest.get("metadata", {}).get("namespace", "default")

        # Build the correct REST path from apiVersion + kind
        resource_map = {
            "Pod": ("api/v1", "pods"),
            "Deployment": ("apis/apps/v1", "deployments"),
            "Service": ("api/v1", "services"),
            "ConfigMap": ("api/v1", "configmaps"),
            "Secret": ("api/v1", "secrets"),
        }
        api_prefix, resource = resource_map.get(kind, ("api/v1", kind.lower() + "s"))
        path = f"/{api_prefix}/namespaces/{ns}/{resource}/{name}"

        data = await self._patch(
            path + f"?fieldManager={field_manager}&force=true",
            manifest,
            content_type="application/apply-patch+yaml",
        )
        meta = data.get("metadata", {})
        return {
            "kind": data.get("kind"),
            "name": meta.get("name"),
            "namespace": meta.get("namespace"),
            "uid": meta.get("uid"),
        }
