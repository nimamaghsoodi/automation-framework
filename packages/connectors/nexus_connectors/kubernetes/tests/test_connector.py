import pytest
import respx
import httpx

from nexus_connectors.kubernetes.connector import KubernetesConnector

CREDS = {"server_url": "https://k8s.example.com", "token": "test-token"}


@pytest.mark.asyncio
@respx.mock
async def test_list_pods():
    respx.get("https://k8s.example.com/api/v1/namespaces/default/pods").mock(
        return_value=httpx.Response(200, json={
            "items": [
                {"metadata": {"name": "pod-1"}, "status": {"phase": "Running", "containerStatuses": [{"ready": True}]}}
            ]
        })
    )
    c = KubernetesConnector(credentials=CREDS)
    result = await c.execute_action("list_pods", {"namespace": "default"})
    assert result["pods"][0]["name"] == "pod-1"
    assert result["pods"][0]["ready"] is True


@pytest.mark.asyncio
@respx.mock
async def test_get_pod_status():
    respx.get("https://k8s.example.com/api/v1/namespaces/default/pods/my-pod").mock(
        return_value=httpx.Response(200, json={"status": {"phase": "Running", "conditions": [], "containerStatuses": []}})
    )
    c = KubernetesConnector(credentials=CREDS)
    result = await c.execute_action("get_pod_status", {"namespace": "default", "pod_name": "my-pod"})
    assert result["phase"] == "Running"
