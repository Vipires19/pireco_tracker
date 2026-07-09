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


class LoggingSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    log_level: str = "INFO"
    log_format: str = "json"


class SecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    jwt_secret_key: str = Field(
        default="change-me-in-production-use-long-random-string",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(default=15, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    jwt_refresh_token_expire_days: int = Field(default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE")
    login_rate_limit: int = Field(default=5, alias="LOGIN_RATE_LIMIT")
    login_rate_limit_window_seconds: int = Field(default=60, alias="LOGIN_RATE_LIMIT_WINDOW_SECONDS")
    refresh_token_cookie_name: str = "refresh_token"


class MetricsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    metrics_enabled: bool = True
    health_host: str = "0.0.0.0"
    health_port: int = Field(default=8000, alias="HEALTH_PORT")
