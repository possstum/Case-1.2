from __future__ import annotations

from functools import lru_cache
import logging
from typing import Optional

from redis import Redis
from rq import Queue

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_redis_connection() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)


def get_queue(name: Optional[str] = None) -> Queue:
    settings = get_settings()
    queue_name = name or settings.rq_default_queue
    return Queue(queue_name, connection=get_redis_connection())


class RQSyncJobScheduler:
    def schedule(
        self,
        *,
        job_id: str,
        queue_name: str,
    ) -> Optional[str]:
        try:
            queue = get_queue(name=queue_name)
            rq_job = queue.enqueue("app.tasks.sync_jobs.run_sync_job", job_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "sync_job_enqueue_failed queue=%s error=%s",
                queue_name,
                exc.__class__.__name__,
            )
            return None
        return rq_job.id


def clear_queue_caches() -> None:
    get_redis_connection.cache_clear()
