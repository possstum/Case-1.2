from __future__ import annotations

from typing import Any

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError


class HealthService:
    def __init__(self, *, engine: Engine, redis_client: Redis, require_redis: bool) -> None:
        self.engine = engine
        self.redis_client = redis_client
        self.require_redis = require_redis

    def check(self) -> dict[str, Any]:
        database_status = self._check_database()
        redis_status = self._check_redis()

        is_healthy = database_status["status"] == "ok" and (
            redis_status["status"] == "ok" or not self.require_redis
        )

        return {
            "status": "ok" if is_healthy else "degraded",
            "app": {
                "status": "ok",
                "detail": "ready",
            },
            "database": database_status,
            "redis": redis_status,
        }

    def _check_database(self) -> dict[str, str]:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            return {
                "status": "error",
                "detail": str(exc.__class__.__name__),
            }

        return {
            "status": "ok",
            "detail": "reachable",
        }

    def _check_redis(self) -> dict[str, str]:
        try:
            self.redis_client.ping()
        except RedisError as exc:
            return {
                "status": "error",
                "detail": str(exc.__class__.__name__),
            }

        return {
            "status": "ok",
            "detail": "reachable",
        }
