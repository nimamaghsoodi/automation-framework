import pytest
import respx
import httpx

from nexus_connectors.teams.connector import TeamsConnector


TOKEN_RESP = {"access_token": "tok_test", "token_type": "Bearer", "expires_in": 3600}


@pytest.mark.asyncio
@respx.mock
async def test_send_channel_message():
    respx.post("https://login.microsoftonline.com/tenant123/oauth2/v2.0/token").mock(
        return_value=httpx.Response(200, json=TOKEN_RESP)
    )
    respx.post("https://graph.microsoft.com/v1.0/teams/team1/channels/chan1/messages").mock(
        return_value=httpx.Response(201, json={"id": "msg123", "createdDateTime": "2026-09-13T10:00:00Z"})
    )
    c = TeamsConnector(credentials={"tenant_id": "tenant123", "client_id": "cid", "client_secret": "csec"})
    result = await c.execute_action("send_channel_message", {
        "team_id": "team1", "channel_id": "chan1", "message": "Hello Teams!"
    })
    assert result["message_id"] == "msg123"


@pytest.mark.asyncio
@respx.mock
async def test_test_connection_with_access_token():
    c = TeamsConnector(credentials={"access_token": "tok_direct"})
    result = await c.test_connection()
    assert result["ok"] is True
