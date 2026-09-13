"""
Global connector registry (in the SDK, not the app) so connector packages
can self-register without importing from the app layer.
"""
from __future__ import annotations

import importlib
import pkgutil

_registry: dict[str, type] = {}


def register(key: str, cls: type) -> None:
    _registry[key] = cls


def get_connector_class(key: str) -> type:
    if key not in _registry:
        raise KeyError(f"No connector registered for key: {key!r}. Available: {list(_registry)}")
    return _registry[key]


def all_keys() -> list[str]:
    return list(_registry.keys())


def autodiscover(package: str = "nexus_connectors") -> None:
    try:
        pkg = importlib.import_module(package)
    except ModuleNotFoundError:
        return
    for _finder, name, _ispkg in pkgutil.walk_packages(pkg.__path__, prefix=f"{package}."):
        importlib.import_module(name)
