"""Application configuration models."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed runtime configuration."""

    model_config = SettingsConfigDict(
        env_file=".env.backend",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Instragram API")
    app_env: str = Field(default="local", alias="APP_ENV")
    debug: bool = Field(default=False, alias="DEBUG")

    secret_key: str = Field(default="change-me", alias="SECRET_KEY")

    database_url: str = Field(
        default="postgresql+asyncpg://app:app@postgres:5432/instagram",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    minio_endpoint: str = Field(default="minio:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minio", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minio123", alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="instagram-media", alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_minutes: int = Field(
        default=60 * 24 * 7, alias="REFRESH_TOKEN_EXPIRE_MINUTES"
    )

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a normalized list."""
        if isinstance(self.cors_origins, str):
            origins = self.cors_origins.split(",")
        else:
            origins = self.cors_origins
        return [origin.strip() for origin in origins if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Memoized settings accessor to avoid repeated parsing."""
    return Settings()


settings: Settings = get_settings()
