import pytest
import respx
import httpx

from nexus_connectors.http_rest.connector import HttpRestConnector


@pytest.mark.asyncio
@respx.mock
async def test_get_request():
    respx.get("https://api.example.com/users").mock(
        return_value=httpx.Response(200, json={"users": [{"id": 1}]})
    )
    connector = HttpRestConnector(credentials={"auth_type": "none"})
    result = await connector.execute_action("request", {
        "url": "https://api.example.com/users",
        "method": "GET",
    })
    assert result["status_code"] == 200
    assert result["ok"] is True
    assert result["body"]["users"][0]["id"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_post_with_bearer():
    respx.post("https://api.example.com/items").mock(
        return_value=httpx.Response(201, json={"id": 42})
    )
    connector = HttpRestConnector(credentials={"auth_type": "bearer", "api_key": "tok_secret"})
    result = await connector.execute_action("request", {
        "url": "https://api.example.com/items",
        "method": "POST",
        "body": {"name": "test"},
    })
    assert result["status_code"] == 201
    assert result["body"]["id"] == 42


@pytest.mark.asyncio
async def test_unknown_action_raises():
    connector = HttpRestConnector(credentials={})
    with pytest.raises(Exception, match="Unknown action"):
        await connector.execute_action("nonexistent", {})
