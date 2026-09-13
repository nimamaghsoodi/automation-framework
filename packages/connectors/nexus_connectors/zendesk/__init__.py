from nexus_connectors.zendesk.connector import ZendeskConnector
from nexus_sdk import register

register("zendesk", ZendeskConnector)

__all__ = ["ZendeskConnector"]
