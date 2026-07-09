from functools import lru_cache

from pydantic_settings import SettingsConfigDict

from app.config.base import AppSettings, LoggingSettings, MetricsSettings, RedisSettings, TelemetrySettings


class GatewaySettings(
    AppSettings,
    RedisSettings,
    TelemetrySettings,
    MetricsSettings,
    LoggingSettings,
):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "gateway"
    tcp_host: str = "0.0.0.0"
    tcp_port: int = 5023
    max_connections: int = 10_000
    read_buffer_size: int = 4096
    connection_idle_timeout: int = 300


@lru_cache
def get_settings() -> GatewaySettings:
    return GatewaySettings()
