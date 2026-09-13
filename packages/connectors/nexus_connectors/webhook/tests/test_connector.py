import pytest
from nexus_connectors.webhook.connector import WebhookConnector
from nexus_sdk import ConnectorError


@pytest.mark.asyncio
async def test_handle_inbound_trigger():
    connector = WebhookConnector(credentials={})
    payload = {"headers": {}, "body": {"event": "order.created"}, "query": {}, "method": "POST"}
    result = await connector.handle_trigger("inbound", payload)
    assert result["body"]["event"] == "order.created"


@pytest.mark.asyncio
async def test_execute_action_raises():
    connector = WebhookConnector(credentials={})
    with pytest.raises(ConnectorError):
        await connector.execute_action("any", {})


def test_verify_signature_valid():
    secret = "my-signing-secret"
    import hashlib, hmac
    body = b'{"event": "test"}'
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert WebhookConnector.verify_signature(secret, body, sig) is True


def test_verify_signature_invalid():
    assert WebhookConnector.verify_signature("secret", b"body", "sha256=badhash") is False
