import pytest
import respx
import httpx

from nexus_connectors.jira.connector import JiraConnector

CREDS = {"base_url": "https://testco.atlassian.net", "email": "dev@testco.com", "api_token": "token123"}


@pytest.mark.asyncio
@respx.mock
async def test_create_issue():
    respx.post("https://testco.atlassian.net/rest/api/3/issue").mock(
        return_value=httpx.Response(201, json={"id": "10001", "key": "NEXUS-1", "self": "https://testco.atlassian.net/rest/api/3/issue/10001"})
    )
    c = JiraConnector(credentials=CREDS)
    result = await c.execute_action("create_issue", {
        "project_key": "NEXUS", "summary": "Test issue", "issue_type": "Task"
    })
    assert result["issue_key"] == "NEXUS-1"
    assert "browse/NEXUS-1" in result["url"]


@pytest.mark.asyncio
@respx.mock
async def test_get_issue():
    respx.get("https://testco.atlassian.net/rest/api/3/issue/NEXUS-1").mock(
        return_value=httpx.Response(200, json={
            "key": "NEXUS-1",
            "fields": {"summary": "Test", "status": {"name": "In Progress"}, "assignee": {"displayName": "Alice"}}
        })
    )
    c = JiraConnector(credentials=CREDS)
    result = await c.execute_action("get_issue", {"issue_key": "NEXUS-1"})
    assert result["status"] == "In Progress"
    assert result["assignee"] == "Alice"
