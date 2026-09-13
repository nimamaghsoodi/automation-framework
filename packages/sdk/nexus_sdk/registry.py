"""
Global connector registry (in the SDK) — connectors self-register on import.
Also caches the raw manifest dict so the API can serve it without re-reading disk.
"""
from __future__ import annotations

import importlib
import pkgutil
from typing import Any

import yaml

_registry: dict[str, type] = {}
_manifests: dict[str, dict[str, Any]] = {}


def register(key: str, cls: type) -> None:
    _registry[key] = cls
    if hasattr(cls, "manifest_path"):
        try:
            raw = yaml.safe_load(cls.manifest_path.read_text())
            _manifests[key] = raw
        except Exception:
            pass


def get_connector_class(key: str) -> type:
    if key not in _registry:
        raise KeyError(f"No connector registered for key: {key!r}. Available: {list(_registry)}")
    return _registry[key]


def get_manifest(key: str) -> dict[str, Any] | None:
    return _manifests.get(key)


def all_manifests() -> dict[str, dict[str, Any]]:
    return dict(_manifests)


def all_keys() -> list[str]:
    return list(_registry.keys())


def autodiscover(package: str = "nexus_connectors") -> None:
    try:
        pkg = importlib.import_module(package)
    except ModuleNotFoundError:
        return
    for _finder, name, _ispkg in pkgutil.walk_packages(pkg.__path__, prefix=f"{package}."):
        importlib.import_module(name)
