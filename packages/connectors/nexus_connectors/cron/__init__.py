from nexus_connectors.cron.connector import CronConnector
from nexus_sdk import register

register("cron", CronConnector)

__all__ = ["CronConnector"]
