from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "Nexus"
    environment: str = "development"
    debug: bool = False
    secret_key: str = Field(..., description="JWT signing key (32+ random bytes)")

    # Database
    database_url: str = Field(..., description="PostgreSQL async DSN (asyncpg)")
    database_url_sync: str = Field(..., description="PostgreSQL sync DSN (psycopg2, used by Alembic)")

    # Redis / Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Credential encryption
    encryption_key: str = Field(..., description="Fernet symmetric key for credential encryption")

    # Auth
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    # Admin bootstrap user
    admin_email: str = "admin@nexus.local"
    admin_password: str = "admin"

    # OAuth2 — Google
    google_client_id: str | None = None
    google_client_secret: str | None = None

    # OAuth2 — GitHub
    github_client_id: str | None = None
    github_client_secret: str | None = None

    # OAuth2 redirect base (public URL of the API, no trailing slash)
    oauth_redirect_base: str = "http://localhost:8000"

    # Frontend URL (for post-OAuth redirects)
    frontend_url: str = "http://localhost:5173"

    # SAML 2.0 SP configuration
    saml_enabled: bool = False
    saml_sp_entity_id: str = "nexus-sp"
    saml_sp_acs_url: str = "http://localhost:8000/api/v1/auth/saml/acs"
    saml_sp_cert: str | None = None
    saml_sp_private_key: str | None = None
    saml_idp_entity_id: str | None = None
    saml_idp_sso_url: str | None = None
    saml_idp_cert: str | None = None

    # Webhook signing
    webhook_signing_tolerance_seconds: int = 300


settings = Settings()  # type: ignore[call-arg]
