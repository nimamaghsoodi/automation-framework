from nexus_connectors.kubernetes.connector import KubernetesConnector
from nexus_sdk import register

register("kubernetes", KubernetesConnector)

__all__ = ["KubernetesConnector"]
