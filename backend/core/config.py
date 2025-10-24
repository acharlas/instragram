"""Application configuration models."""

from functools import lru_cache
from types import MethodType
from typing import Annotated, Iterable

from pydantic import Field, model_validator
from pydantic.functional_validators import BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_comma_separated(value: object) -> object:
    """Convert comma-separated env strings into trimmed lists."""
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


CommaSeparatedList = Annotated[list[str], BeforeValidator(_split_comma_separated)]
COMMA_SEPARATED_FIELDS = frozenset(
    {"rate_limit_ip_headers", "rate_limit_trusted_proxies", "cors_origins"}
)


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

    secret_key: str = Field(alias="SECRET_KEY")

    database_url: str = Field(
        alias="DATABASE_URL",
    )
    redis_url: str = Field(alias="REDIS_URL")
    rate_limit_requests: int = Field(default=60, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(
        default=60, alias="RATE_LIMIT_WINDOW_SECONDS"
    )
    rate_limit_ip_headers: CommaSeparatedList = Field(
        default_factory=lambda: ["x-forwarded-for"],
        alias="RATE_LIMIT_IP_HEADERS",
    )
    rate_limit_trusted_proxies: CommaSeparatedList = Field(
        default_factory=lambda: ["127.0.0.1/32", "::1/128"],
        alias="RATE_LIMIT_TRUSTED_PROXIES",
    )

    upload_max_bytes: int = Field(
        default=5 * 1024 * 1024, alias="UPLOAD_MAX_BYTES"
    )

    minio_endpoint: str = Field(default="minio:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="instagram-media", alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")

    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=15, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_minutes: int = Field(
        default=60 * 24 * 7, alias="REFRESH_TOKEN_EXPIRE_MINUTES"
    )

    cors_origins: CommaSeparatedList = Field(
        default_factory=lambda: ["http://localhost:3000"],
        alias="CORS_ORIGINS",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_lists(cls, values: dict[str, object]) -> dict[str, object]:
        """Allow comma-separated strings for list fields in env files."""
        for field_name in (
            "rate_limit_ip_headers",
            "rate_limit_trusted_proxies",
            "cors_origins",
        ):
            field_info = cls.model_fields[field_name]
            possible_keys = [field_name]
            if field_info.alias:
                possible_keys.append(field_info.alias)
            for key in possible_keys:
                raw = values.get(key)
                if isinstance(raw, str):
                    normalized = [item.strip() for item in raw.split(",") if item.strip()]
                    values[field_name] = normalized
                    values[key] = normalized
                    break
        return values

    @model_validator(mode="after")
    def _ensure_secret_key(self) -> "Settings":
        """Prevent insecure defaults outside of local/test environments."""
        if not self.secret_key and self.app_env not in {"local", "test"}:
            raise ValueError("SECRET_KEY must be configured for non-local environments")
        return self

    @classmethod
    def _patch_comma_sources(cls, source) -> None:
        """Allow simple CSV values for list settings in env-backed sources."""
        if source is None or getattr(source, "_comma_patch_applied", False):
            return

        original = source.prepare_field_value

        def wrapper(self, field_name, field, value, value_is_complex):
            if (
                field_name in COMMA_SEPARATED_FIELDS
                and isinstance(value, str)
                and value is not None
            ):
                stripped = value.strip()
                if stripped and not stripped.startswith("["):
                    return _split_comma_separated(stripped)
            return original(field_name, field, value, value_is_complex)

        source.prepare_field_value = MethodType(wrapper, source)
        setattr(source, "_comma_patch_applied", True)

    @classmethod
    def settings_customise_sources(  # type: ignore[override]
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        cls._patch_comma_sources(env_settings)
        cls._patch_comma_sources(dotenv_settings)
        return super().settings_customise_sources(
            settings_cls,
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a normalized list."""
        if isinstance(self.cors_origins, str):
            origins: Iterable[str] = self.cors_origins.split(",")
        else:
            origins = self.cors_origins
        return [origin.strip() for origin in origins if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Memoized settings accessor to avoid repeated parsing."""
    return Settings()


settings: Settings = get_settings()
