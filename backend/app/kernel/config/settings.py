from functools import lru_cache

from pydantic_settings import SettingsConfigDict

from app.kernel.config.base import (
    AppSettings,
    AuthSettings,
    DatabaseSettings,
    LoggingSettings,
    MetricsSettings,
    RedisSettings,
    SecuritySettings,
)


class BackendSettings(
    AppSettings,
    DatabaseSettings,
    RedisSettings,
    LoggingSettings,
    SecuritySettings,
    AuthSettings,
    MetricsSettings,
):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "backend"
    api_prefix: str = "/api/v1"


@lru_cache
def get_settings() -> BackendSettings:
    return BackendSettings()
