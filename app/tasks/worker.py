from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import Optional

from rq import SimpleWorker, Worker

from app.core.config import get_settings
from app.tasks.queue import get_redis_connection


def get_worker_class():
    # RQ's forked work-horse crashes on local macOS verification, so use the in-process worker there.
    if sys.platform == "darwin":
        return SimpleWorker
    return Worker


def create_worker(queue_names: Optional[Sequence[str]] = None) -> Worker:
    settings = get_settings()
    names = list(queue_names or [settings.rq_default_queue])
    worker_class = get_worker_class()
    return worker_class(names, connection=get_redis_connection())


def main(argv: Optional[Sequence[str]] = None) -> None:
    worker = create_worker(argv or sys.argv[1:])
    worker.work()


if __name__ == "__main__":
    main()
