from functools import lru_cache

from pydantic_settings import SettingsConfigDict

from app.config.base import (
    AppSettings,
    DatabaseSettings,
    LoggingSettings,
    MetricsSettings,
    RedisSettings,
    TelemetrySettings,
)


class WorkerSettings(
    AppSettings,
    DatabaseSettings,
    RedisSettings,
    TelemetrySettings,
    MetricsSettings,
    LoggingSettings,
):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "worker"
    health_port: int = 9100


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
