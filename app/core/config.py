from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import Engine


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = Field(default="NETvRF", validation_alias="APP_NAME")
    app_env: str = Field(default="development", validation_alias="APP_ENV")
    debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    app_host: str = Field(default="127.0.0.1", validation_alias="APP_HOST")
    app_port: int = Field(default=8000, validation_alias="APP_PORT")
    api_prefix: str = Field(default="", validation_alias="API_PREFIX")
    log_level: str = Field(default="INFO", validation_alias="APP_LOG_LEVEL")
    correlation_id_header: str = Field(
        default="X-Correlation-ID",
        validation_alias="CORRELATION_ID_HEADER",
    )

    database_url: str = Field(
        default="sqlite+pysqlite:///./data/netvrf.db",
        validation_alias="DATABASE_URL",
    )
    sql_echo: bool = Field(default=False, validation_alias="SQL_ECHO")

    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    rq_default_queue: str = Field(default="default", validation_alias="RQ_DEFAULT_QUEUE")
    health_require_redis: bool = Field(
        default=False,
        validation_alias="HEALTH_REQUIRE_REDIS",
    )
    match_candidate_threshold: float = Field(
        default=0.35,
        validation_alias="MATCH_CANDIDATE_THRESHOLD",
    )
    match_ambiguous_threshold: float = Field(
        default=0.6,
        validation_alias="MATCH_AMBIGUOUS_THRESHOLD",
    )
    match_auto_threshold: float = Field(
        default=0.88,
        validation_alias="MATCH_AUTO_THRESHOLD",
    )
    match_gap_threshold: float = Field(
        default=0.05,
        validation_alias="MATCH_GAP_THRESHOLD",
    )
    search_default_limit: int = Field(
        default=5,
        validation_alias="SEARCH_DEFAULT_LIMIT",
    )
    search_max_limit: int = Field(
        default=10,
        validation_alias="SEARCH_MAX_LIMIT",
    )
    search_cache_stale_seconds: int = Field(
        default=300,
        validation_alias="SEARCH_CACHE_STALE_SECONDS",
    )
    search_cache_ttl_seconds: int = Field(
        default=1800,
        validation_alias="SEARCH_CACHE_TTL_SECONDS",
    )
    search_provider_timeout_seconds: float = Field(
        default=5.0,
        validation_alias="SEARCH_PROVIDER_TIMEOUT_SECONDS",
    )
    provider_http_timeout_seconds: float = Field(
        default=5.0,
        validation_alias="PROVIDER_HTTP_TIMEOUT_SECONDS",
    )
    search_provider_max_attempts: int = Field(
        default=1,
        validation_alias="SEARCH_PROVIDER_MAX_ATTEMPTS",
    )
    search_provider_retry_backoff_seconds: float = Field(
        default=0.0,
        validation_alias="SEARCH_PROVIDER_RETRY_BACKOFF_SECONDS",
    )
    sync_provider_max_attempts: int = Field(
        default=1,
        validation_alias="SYNC_PROVIDER_MAX_ATTEMPTS",
    )
    sync_provider_timeout_seconds: float = Field(
        default=5.0,
        validation_alias="SYNC_PROVIDER_TIMEOUT_SECONDS",
    )
    sync_provider_retry_backoff_seconds: float = Field(
        default=0.0,
        validation_alias="SYNC_PROVIDER_RETRY_BACKOFF_SECONDS",
    )
    search_rate_limit: int = Field(
        default=30,
        validation_alias="SEARCH_RATE_LIMIT",
    )
    search_rate_window_seconds: int = Field(
        default=60,
        validation_alias="SEARCH_RATE_WINDOW_SECONDS",
    )
    sync_rate_limit: int = Field(
        default=5,
        validation_alias="SYNC_RATE_LIMIT",
    )
    sync_rate_window_seconds: int = Field(
        default=60,
        validation_alias="SYNC_RATE_WINDOW_SECONDS",
    )
    youtube_music_token: Optional[str] = Field(
        default=None,
        validation_alias="YOUTUBE_MUSIC_TOKEN",
    )
    yandex_music_token: Optional[str] = Field(
        default=None,
        validation_alias="YANDEX_MUSIC_TOKEN",
    )

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def sqlite_path(self) -> Optional[Path]:
        if not self.is_sqlite:
            return None

        if "///" not in self.database_url:
            return None

        raw_path = self.database_url.split("///", 1)[1]
        if raw_path == ":memory:":
            return None

        return Path(raw_path).expanduser()

    @property
    def sqlite_connect_args(self) -> Dict[str, Any]:
        if not self.is_sqlite:
            return {}
        return {"check_same_thread": False}

    def get_engine(self) -> Engine:
        from app.db.session import get_engine

        return get_engine()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
