from __future__ import annotations

import logging
import time

from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class FixedWindowRateLimiter:
    def __init__(self, *, redis_client: Redis, prefix: str = "rate-limit") -> None:
        self.redis_client = redis_client
        self.prefix = prefix

    def allow(
        self,
        *,
        namespace: str,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> bool:
        bucket = int(time.time() // window_seconds)
        key = f"{self.prefix}:{namespace}:{identifier}:{bucket}"

        try:
            current = self.redis_client.incr(key)
            if current == 1:
                self.redis_client.expire(key, window_seconds)
        except RedisError as exc:
            logger.warning("rate_limit_backend_unavailable error=%s", exc.__class__.__name__)
            return True

        return current <= limit
