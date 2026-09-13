# Thin re-export of the SDK registry so app code can import from a consistent location.
from nexus_sdk.registry import register, get_connector_class, all_keys, autodiscover

__all__ = ["register", "get_connector_class", "all_keys", "autodiscover"]
