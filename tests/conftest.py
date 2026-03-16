from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_health_service
from app.core.config import clear_settings_cache
from app.db.session import clear_session_caches, get_session_factory
from app.main import create_app
from app.tasks.queue import clear_queue_caches

ROOT = Path(__file__).resolve().parents[1]


class StubHealthService:
    def check(self) -> dict[str, object]:
        return {
            "status": "ok",
            "app": {"status": "ok", "detail": "ready"},
            "database": {"status": "ok", "detail": "reachable"},
            "redis": {"status": "ok", "detail": "reachable"},
        }


def reset_runtime_caches() -> None:
    clear_queue_caches()
    clear_session_caches()
    clear_settings_cache()


@pytest.fixture()
def app():
    application = create_app()
    application.dependency_overrides[get_health_service] = lambda: StubHealthService()
    return application


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def sqlite_database_url(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    database_url = f"sqlite+pysqlite:///{tmp_path / 'test.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    reset_runtime_caches()
    yield database_url
    reset_runtime_caches()


@pytest.fixture()
def alembic_config(sqlite_database_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    return config


@pytest.fixture()
def migrated_sqlite_database(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")


@pytest.fixture()
def db_session(migrated_sqlite_database) -> Iterator[Session]:
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.rollback()
    finally:
        session.close()
