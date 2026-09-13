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
    # 32-byte Fernet key, base64-url-encoded — generate with: Fernet.generate_key()
    encryption_key: str = Field(..., description="Fernet symmetric key for credential encryption")

    # Auth
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    # Webhook signing
    webhook_signing_tolerance_seconds: int = 300


settings = Settings()  # type: ignore[call-arg]
