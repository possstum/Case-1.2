from __future__ import annotations

import pytest

from app.core.config import clear_settings_cache
from app.tasks.queue import RQSyncJobScheduler, clear_queue_caches, get_queue, get_redis_connection
from app.tasks.worker import create_worker, get_worker_class


@pytest.fixture(autouse=True)
def reset_queue_runtime() -> None:
    clear_settings_cache()
    clear_queue_caches()
    yield
    clear_queue_caches()
    clear_settings_cache()


def test_get_redis_connection_uses_binary_safe_decoding(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6380/7")

    redis_client = get_redis_connection()

    assert redis_client.connection_pool.connection_kwargs["decode_responses"] is False
    assert redis_client.connection_pool.connection_kwargs["port"] == 6380
    assert redis_client.connection_pool.connection_kwargs["db"] == 7


def test_get_queue_uses_default_queue_and_shared_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RQ_DEFAULT_QUEUE", "sync-default")
    clear_settings_cache()

    redis_connection = object()
    calls: dict[str, object] = {}

    class FakeQueue:
        def __init__(self, name: str, connection: object) -> None:
            calls["name"] = name
            calls["connection"] = connection

    monkeypatch.setattr("app.tasks.queue.get_redis_connection", lambda: redis_connection)
    monkeypatch.setattr("app.tasks.queue.Queue", FakeQueue)

    queue = get_queue()

    assert isinstance(queue, FakeQueue)
    assert calls == {"name": "sync-default", "connection": redis_connection}


def test_scheduler_enqueues_sync_job(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    class FakeJob:
        id = "rq-job-42"

    class FakeQueue:
        def enqueue(self, func: str, *args: object) -> FakeJob:
            calls["func"] = func
            calls["args"] = args
            return FakeJob()

    monkeypatch.setattr("app.tasks.queue.get_queue", lambda name=None: FakeQueue())

    job_id = RQSyncJobScheduler().schedule(job_id="sync-job-9", queue_name="default")

    assert job_id == "rq-job-42"
    assert calls == {
        "func": "app.tasks.sync_jobs.run_sync_job",
        "args": ("sync-job-9",),
    }


def test_get_worker_class_uses_simple_worker_on_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.tasks.worker.sys.platform", "darwin")

    worker_class = get_worker_class()

    assert worker_class.__name__ == "SimpleWorker"


def test_get_worker_class_uses_standard_worker_off_macos(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.tasks.worker.sys.platform", "linux")

    worker_class = get_worker_class()

    assert worker_class.__name__ == "Worker"


def test_create_worker_uses_default_queue_and_binary_safe_connection_on_macos(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6380/9")
    monkeypatch.setenv("RQ_DEFAULT_QUEUE", "worker-default")
    monkeypatch.setattr("app.tasks.worker.sys.platform", "darwin")
    clear_settings_cache()
    clear_queue_caches()

    calls: dict[str, object] = {}

    class FakeSimpleWorker:
        def __init__(self, queues: list[str], connection) -> None:
            calls["queues"] = queues
            calls["connection"] = connection

    monkeypatch.setattr("app.tasks.worker.SimpleWorker", FakeSimpleWorker)

    worker = create_worker()

    assert isinstance(worker, FakeSimpleWorker)
    assert calls["queues"] == ["worker-default"]
    connection = calls["connection"]
    assert connection.connection_pool.connection_kwargs["decode_responses"] is False
    assert connection.connection_pool.connection_kwargs["port"] == 6380
    assert connection.connection_pool.connection_kwargs["db"] == 9
