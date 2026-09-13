"""
Pydantic schema for connector manifest.yaml files.
Every connector ships a manifest that drives:
  - what the UI renders (auth form, action list, input schemas)
  - what the engine knows about the connector at registration time
"""
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AuthType(str, Enum):
    none = "none"
    api_key = "api_key"
    bearer = "bearer"
    basic = "basic"
    oauth2 = "oauth2"
    iam = "iam"          # cloud SDK / IAM role / service account
    webhook_only = "webhook_only"


class CredentialField(BaseModel):
    name: str
    label: str
    type: str = "string"  # string | secret | url | select
    required: bool = True
    options: list[str] | None = None   # for type=select
    placeholder: str | None = None
    help_text: str | None = None


class OAuth2Config(BaseModel):
    authorization_url: str
    token_url: str
    scopes: list[str] = Field(default_factory=list)
    extra_params: dict[str, str] = Field(default_factory=dict)


class AuthConfig(BaseModel):
    type: AuthType
    fields: list[CredentialField] = Field(default_factory=list)
    oauth2: OAuth2Config | None = None


class SchemaProperty(BaseModel):
    type: str
    title: str | None = None
    description: str | None = None
    default: Any = None
    enum: list[Any] | None = None
    items: "SchemaProperty | None" = None       # for array types
    properties: "dict[str, SchemaProperty] | None" = None  # for object types
    required: list[str] | None = None


class ActionSchema(BaseModel):
    """JSON-Schema-like descriptor for an action's input or output."""
    type: str = "object"
    properties: dict[str, SchemaProperty] = Field(default_factory=dict)
    required: list[str] = Field(default_factory=list)


class ActionManifest(BaseModel):
    key: str
    name: str
    description: str = ""
    input_schema: ActionSchema = Field(default_factory=ActionSchema)
    output_schema: ActionSchema = Field(default_factory=ActionSchema)


class TriggerManifest(BaseModel):
    key: str
    name: str
    description: str = ""
    # For webhook triggers: the path suffix appended to the flow's webhook URL
    webhook_path: str | None = None
    # For polling triggers: suggested poll interval in seconds
    poll_interval_seconds: int | None = None
    output_schema: ActionSchema = Field(default_factory=ActionSchema)


class ConnectorManifest(BaseModel):
    """
    Top-level manifest schema. Every connector's manifest.yaml is validated
    against this model at registration and at connector load time.
    """
    key: str = Field(..., description="Unique connector identifier, e.g. 'slack'")
    name: str
    version: str = Field(..., description="Semver string, e.g. '1.0.0'")
    category: str = Field(..., description="communication|ticketing|cloud|database|devops|...")
    description: str = ""
    icon_url: str | None = None
    # Minimum OAuth scopes / IAM actions required — document least-privilege
    required_scopes: list[str] = Field(default_factory=list)
    auth: AuthConfig
    actions: list[ActionManifest] = Field(default_factory=list)
    triggers: list[TriggerManifest] = Field(default_factory=list)
