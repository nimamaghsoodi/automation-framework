from nexus_connectors.webhook.connector import WebhookConnector
from nexus_sdk import register

register("webhook", WebhookConnector)

__all__ = ["WebhookConnector"]
