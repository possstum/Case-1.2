from __future__ import annotations

from sqlalchemy import func, select

from app.db.models import SyncJob
from app.db.repositories.sync_jobs import SyncJobRepository
from tests.test_support import AllowAllLimiter, DenyAllLimiter, RecordingSyncScheduler, create_test_client, seed_catalog


def test_post_sync_enqueues_job_and_persists_record(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    ids = seed_catalog(db_session)
    scheduler = RecordingSyncScheduler(rq_job_id="rq-55")
    headers = {"X-Correlation-ID": "cid-sync-accepted"}

    with create_test_client(sync_scheduler=scheduler, limiter=AllowAllLimiter()) as client:
        response = client.post(f"/sync/artist/{ids['artist_id']}", headers=headers)

    assert response.status_code == 202
    assert response.headers["X-Correlation-ID"] == headers["X-Correlation-ID"]
    payload = response.json()
    assert payload["created"] is True
    assert payload["job"]["status"] == "queued"
    assert scheduler.calls[0]["queue_name"] == "default"

    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(SyncJob)) == 1
    sync_job = db_session.scalar(select(SyncJob))
    assert sync_job is not None
    assert sync_job.rq_job_id == "rq-55"
    assert sync_job.target_id == str(ids["artist_id"])


def test_post_sync_rate_limit_returns_429_without_persisting_job(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    ids = seed_catalog(db_session)
    headers = {"X-Correlation-ID": "cid-sync-rate-limit"}

    with create_test_client(limiter=DenyAllLimiter()) as client:
        response = client.post(f"/sync/artist/{ids['artist_id']}", headers=headers)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limit_exceeded"
    assert response.headers["X-Correlation-ID"] == headers["X-Correlation-ID"]
    assert response.json()["error"]["correlation_id"] == headers["X-Correlation-ID"]

    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(SyncJob)) == 0


def test_post_sync_reuses_active_job_for_same_target(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    ids = seed_catalog(db_session)
    scheduler = RecordingSyncScheduler(rq_job_id="rq-77")

    with create_test_client(sync_scheduler=scheduler, limiter=AllowAllLimiter()) as client:
        first_response = client.post(f"/sync/artist/{ids['artist_id']}")
        second_response = client.post(f"/sync/artist/{ids['artist_id']}")

    assert first_response.status_code == 202
    assert second_response.status_code == 202
    assert first_response.json()["job"]["id"] == second_response.json()["job"]["id"]
    assert second_response.json()["created"] is False
    assert len(scheduler.calls) == 1


def test_get_job_returns_existing_status(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    repository = SyncJobRepository(db_session)
    sync_job = repository.create(
        kind="artist",
        target_id="42",
        queue_name="default",
        status="finished",
        payload_json={"kind": "artist", "target_id": "42"},
    )
    repository.mark_finished(sync_job, result_json={"updated_count": 2})
    db_session.commit()

    with create_test_client() as client:
        response = client.get(f"/jobs/{sync_job.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == sync_job.id
    assert payload["status"] == "finished"
    assert payload["result_json"]["updated_count"] == 2
