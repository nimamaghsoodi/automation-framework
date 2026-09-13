from nexus_connectors.aws.connector import AWSConnector
from nexus_sdk import register

register("aws", AWSConnector)

__all__ = ["AWSConnector"]
