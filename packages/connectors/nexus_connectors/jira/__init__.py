from nexus_connectors.jira.connector import JiraConnector
from nexus_sdk import register

register("jira", JiraConnector)

__all__ = ["JiraConnector"]
