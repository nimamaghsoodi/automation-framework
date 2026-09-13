from nexus_connectors.teams.connector import TeamsConnector
from nexus_sdk import register

register("teams", TeamsConnector)

__all__ = ["TeamsConnector"]
