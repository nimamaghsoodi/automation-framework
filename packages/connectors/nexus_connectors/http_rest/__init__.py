from nexus_connectors.http_rest.connector import HttpRestConnector
from nexus_sdk import register

register("http_rest", HttpRestConnector)

__all__ = ["HttpRestConnector"]
