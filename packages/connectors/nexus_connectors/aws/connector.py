from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from nexus_sdk import Connector, ConnectorError


class AWSConnector(Connector):
    manifest_path = Path(__file__).parent / "manifest.yaml"

    def _boto_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "aws_access_key_id": self.credentials.get("aws_access_key_id"),
            "aws_secret_access_key": self.credentials.get("aws_secret_access_key"),
            "region_name": self.credentials.get("aws_region", "us-east-1"),
        }
        if token := self.credentials.get("aws_session_token"):
            kwargs["aws_session_token"] = token
        return kwargs

    def _sqs(self):
        import boto3
        return boto3.client("sqs", **self._boto_kwargs())

    def _lambda(self):
        import boto3
        return boto3.client("lambda", **self._boto_kwargs())

    async def test_connection(self) -> dict[str, Any]:
        def _check():
            import boto3
            sts = boto3.client("sts", **self._boto_kwargs())
            identity = sts.get_caller_identity()
            return {"ok": True, "account": identity.get("Account"), "arn": identity.get("Arn")}
        try:
            return await asyncio.to_thread(_check)
        except Exception as exc:
            raise ConnectorError(str(exc), retriable=False)

    async def execute_action(self, action_key: str, inputs: dict[str, Any]) -> dict[str, Any]:
        return await self._dispatch(action_key, inputs)

    async def action_sqs_send_message(self, inputs: dict[str, Any]) -> dict[str, Any]:
        def _send():
            kwargs: dict[str, Any] = {
                "QueueUrl": inputs["queue_url"],
                "MessageBody": inputs["message_body"],
                "DelaySeconds": int(inputs.get("delay_seconds", 0)),
            }
            if gid := inputs.get("message_group_id"):
                kwargs["MessageGroupId"] = gid
            try:
                resp = self._sqs().send_message(**kwargs)
                return {"message_id": resp["MessageId"], "md5_of_body": resp.get("MD5OfMessageBody", "")}
            except Exception as exc:
                raise ConnectorError(str(exc), retriable=True)
        return await asyncio.to_thread(_send)

    async def action_sqs_receive_messages(self, inputs: dict[str, Any]) -> dict[str, Any]:
        def _receive():
            sqs = self._sqs()
            try:
                resp = sqs.receive_message(
                    QueueUrl=inputs["queue_url"],
                    MaxNumberOfMessages=min(int(inputs.get("max_messages", 1)), 10),
                    WaitTimeSeconds=int(inputs.get("wait_time_seconds", 0)),
                )
                messages = resp.get("Messages", [])
                if inputs.get("delete_after_receive") and messages:
                    entries = [{"Id": str(i), "ReceiptHandle": m["ReceiptHandle"]} for i, m in enumerate(messages)]
                    sqs.delete_message_batch(QueueUrl=inputs["queue_url"], Entries=entries)
                return {"messages": [{"body": m.get("Body"), "receipt_handle": m.get("ReceiptHandle"), "message_id": m.get("MessageId")} for m in messages]}
            except Exception as exc:
                raise ConnectorError(str(exc), retriable=True)
        return await asyncio.to_thread(_receive)

    async def action_lambda_invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
        def _invoke():
            payload = inputs.get("payload", {})
            try:
                resp = self._lambda().invoke(
                    FunctionName=inputs["function_name"],
                    InvocationType=inputs.get("invocation_type", "RequestResponse"),
                    Payload=json.dumps(payload).encode(),
                )
                result: dict[str, Any] = {
                    "status_code": resp.get("StatusCode"),
                    "function_error": resp.get("FunctionError"),
                }
                if "Payload" in resp:
                    try:
                        result["payload"] = json.loads(resp["Payload"].read())
                    except Exception:
                        result["payload"] = {}
                return result
            except Exception as exc:
                raise ConnectorError(str(exc), retriable=True)
        return await asyncio.to_thread(_invoke)
