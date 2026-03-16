from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from redis import Redis
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def _ensure_sqlite_directory() -> None:
    settings = get_settings()
    sqlite_path = settings.sqlite_path
    if sqlite_path is None:
        return

    Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)


@event.listens_for(Engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    module_name = dbapi_connection.__class__.__module__
    if "sqlite3" not in module_name:
        return

    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
    finally:
        cursor.close()


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    _ensure_sqlite_directory()
    return create_engine(
        settings.database_url,
        connect_args=settings.sqlite_connect_args,
        echo=settings.sql_echo,
        future=True,
        pool_pre_ping=not settings.is_sqlite,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker:
    return sessionmaker(
        bind=get_engine(),
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)


def clear_session_caches() -> None:
    get_session_factory.cache_clear()
    get_engine.cache_clear()
    get_redis_client.cache_clear()
