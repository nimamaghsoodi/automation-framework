"""
Connector abstract base class. Every connector package must subclass this.

Usage pattern (client code inside the execution engine):
    connector = MyConnector(credentials={"api_token": "..."})
    result = await connector.execute_action("send_message", {"channel": "#ops", "text": "hi"})
"""
from __future__ import annotations

import abc
import importlib
import os
from pathlib import Path
from typing import Any

import yaml

from nexus_sdk.manifest import ConnectorManifest


class ConnectorError(Exception):
    """Raised when a connector action fails in a way the engine should surface."""

    def __init__(self, message: str, retriable: bool = False, details: dict | None = None):
        super().__init__(message)
        self.retriable = retriable
        self.details = details or {}


class Connector(abc.ABC):
    """
    Base class every connector must implement.

    Subclasses override:
      - manifest_path  — class-level Path to manifest.yaml
      - execute_action — dispatch to the right action handler
      - test_connection — validate credentials are working

    Convention: define one method per action key named `action_<key>`,
    then delegate from execute_action. Use the provided helper _dispatch().
    """

    # Subclasses set this to Path(__file__).parent / "manifest.yaml"
    manifest_path: Path

    def __init__(self, credentials: dict[str, Any]):
        self.credentials = credentials
        self._manifest: ConnectorManifest | None = None

    @property
    def manifest(self) -> ConnectorManifest:
        if self._manifest is None:
            raw = yaml.safe_load(self.manifest_path.read_text())
            self._manifest = ConnectorManifest.model_validate(raw)
        return self._manifest

    @abc.abstractmethod
    async def test_connection(self) -> dict[str, Any]:
        """
        Validate that credentials work. Return {"ok": True} on success,
        or raise ConnectorError on failure.
        """

    @abc.abstractmethod
    async def execute_action(self, action_key: str, inputs: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the named action with the given inputs.
        Returns the action's output dict.
        Raises ConnectorError on failure.
        """

    async def handle_trigger(self, trigger_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Parse an inbound trigger payload (e.g. a webhook body) and return
        a normalized output matching the trigger's output_schema.
        Override for connectors that have triggers.
        """
        raise NotImplementedError(f"Connector {self.manifest.key!r} has no trigger handler for {trigger_key!r}")

    def _dispatch(self, action_key: str, inputs: dict[str, Any]) -> Any:
        """
        Helper: call self.action_<key>(inputs) by convention, so execute_action
        implementations can be a one-liner.
        """
        method_name = f"action_{action_key}"
        method = getattr(self, method_name, None)
        if method is None:
            raise ConnectorError(f"Unknown action: {action_key!r}", retriable=False)
        return method(inputs)


def load_manifest(manifest_path: Path) -> ConnectorManifest:
    raw = yaml.safe_load(manifest_path.read_text())
    return ConnectorManifest.model_validate(raw)
