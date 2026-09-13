from nexus_connectors.postgres.connector import PostgresConnector
from nexus_sdk import register

register("postgres", PostgresConnector)

__all__ = ["PostgresConnector"]
