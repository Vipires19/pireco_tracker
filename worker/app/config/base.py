from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    service_name: str = "tracker"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(
        default="postgresql+asyncpg://tracker:tracker_secret@localhost:5432/vehicle_tracker",
        alias="DATABASE_URL",
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    redis_session_key_prefix: str = "tracker:session:"


class TelemetrySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    redis_stream_key: str = "tracker:events"
    redis_dead_letter_stream_key: str = "tracker:dead-letter"
    redis_stream_maxlen: int = 100_000
    redis_consumer_group: str = "tracker-workers"
    redis_consumer_name: str = "worker-1"
    redis_stream_read_count: int = 10
    redis_stream_block_ms: int = 5000
    worker_max_retries: int = 3
    worker_retry_backoff_ms: int = 500


class MetricsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    metrics_enabled: bool = True
    health_host: str = "0.0.0.0"
    health_port: int = Field(default=9100, alias="WORKER_HEALTH_PORT")


class LoggingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    log_level: str = "INFO"
    log_format: str = "json"
