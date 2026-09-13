import pytest
from unittest.mock import patch, MagicMock
from nexus_connectors.aws.connector import AWSConnector

CREDS = {"aws_access_key_id": "AKIA_TEST", "aws_secret_access_key": "secret", "aws_region": "eu-west-1"}


@pytest.mark.asyncio
async def test_sqs_send_message():
    mock_sqs = MagicMock()
    mock_sqs.send_message.return_value = {"MessageId": "msg-001", "MD5OfMessageBody": "abc123"}
    with patch.object(AWSConnector, "_sqs", return_value=mock_sqs):
        c = AWSConnector(credentials=CREDS)
        result = await c.execute_action("sqs_send_message", {
            "queue_url": "https://sqs.eu-west-1.amazonaws.com/123/test-queue",
            "message_body": '{"event": "order.created"}',
        })
    assert result["message_id"] == "msg-001"


@pytest.mark.asyncio
async def test_lambda_invoke():
    payload_bytes = MagicMock()
    payload_bytes.read.return_value = b'{"result": "ok"}'
    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {"StatusCode": 200, "Payload": payload_bytes}
    with patch.object(AWSConnector, "_lambda", return_value=mock_lambda):
        c = AWSConnector(credentials=CREDS)
        result = await c.execute_action("lambda_invoke", {
            "function_name": "my-function",
            "payload": {"key": "value"},
        })
    assert result["status_code"] == 200
    assert result["payload"]["result"] == "ok"
