import pytest
import respx
import httpx

from nexus_connectors.zendesk.connector import ZendeskConnector

CREDS = {"subdomain": "testco", "email": "agent@testco.com", "api_token": "secret123"}


@pytest.mark.asyncio
@respx.mock
async def test_create_ticket():
    respx.post("https://testco.zendesk.com/api/v2/tickets.json").mock(
        return_value=httpx.Response(201, json={"ticket": {"id": 42, "status": "new", "url": "https://testco.zendesk.com/api/v2/tickets/42.json"}})
    )
    c = ZendeskConnector(credentials=CREDS)
    result = await c.execute_action("create_ticket", {"subject": "Test ticket", "body": "Hello"})
    assert result["ticket_id"] == "42"
    assert result["status"] == "new"


@pytest.mark.asyncio
@respx.mock
async def test_get_ticket():
    respx.get("https://testco.zendesk.com/api/v2/tickets/99.json").mock(
        return_value=httpx.Response(200, json={"ticket": {"id": 99, "subject": "Bug", "status": "open", "priority": "high"}})
    )
    c = ZendeskConnector(credentials=CREDS)
    result = await c.execute_action("get_ticket", {"ticket_id": "99"})
    assert result["subject"] == "Bug"
    assert result["status"] == "open"
