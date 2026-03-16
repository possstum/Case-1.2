from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import SyncJob


class SyncJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        kind: str,
        target_id: str,
        queue_name: str,
        status: str = "queued",
        rq_job_id: Optional[str] = None,
        payload_json: Optional[dict[str, Any]] = None,
        job_id: Optional[str] = None,
    ) -> SyncJob:
        sync_job = SyncJob(
            id=job_id or str(uuid4()),
            kind=kind,
            target_id=target_id,
            status=status,
            queue_name=queue_name,
            rq_job_id=rq_job_id,
            payload_json=payload_json or {},
        )
        self.session.add(sync_job)
        self.session.flush()
        return sync_job

    def get(self, job_id: str) -> Optional[SyncJob]:
        return self.session.get(SyncJob, job_id)

    def get_active_for_target(self, *, kind: str, target_id: str) -> Optional[SyncJob]:
        statement = (
            select(SyncJob)
            .where(
                SyncJob.kind == kind,
                SyncJob.target_id == target_id,
                SyncJob.status.in_(("queued", "started")),
            )
            .order_by(SyncJob.created_at.desc())
        )
        return self.session.scalar(statement)

    def set_rq_job_id(self, sync_job: SyncJob, *, rq_job_id: str) -> SyncJob:
        sync_job.rq_job_id = rq_job_id
        self.session.flush()
        return sync_job

    def update_status(
        self,
        sync_job: SyncJob,
        *,
        status: str,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        result_json: Optional[dict[str, Any]] = None,
        error_json: Optional[dict[str, Any]] = None,
        attempts: Optional[int] = None,
    ) -> SyncJob:
        sync_job.status = status
        sync_job.started_at = started_at if started_at is not None else sync_job.started_at
        sync_job.finished_at = finished_at if finished_at is not None else sync_job.finished_at
        sync_job.result_json = result_json if result_json is not None else sync_job.result_json
        sync_job.error_json = error_json if error_json is not None else sync_job.error_json
        if attempts is not None:
            sync_job.attempts = attempts
        self.session.flush()
        return sync_job

    def mark_started(self, sync_job: SyncJob, *, attempts: Optional[int] = None) -> SyncJob:
        return self.update_status(
            sync_job,
            status="started",
            started_at=datetime.now(timezone.utc),
            attempts=attempts if attempts is not None else sync_job.attempts + 1,
        )

    def mark_finished(
        self,
        sync_job: SyncJob,
        *,
        result_json: Optional[dict[str, Any]] = None,
    ) -> SyncJob:
        return self.update_status(
            sync_job,
            status="finished",
            finished_at=datetime.now(timezone.utc),
            result_json=result_json or {},
        )

    def mark_failed(
        self,
        sync_job: SyncJob,
        *,
        error_json: dict[str, Any],
    ) -> SyncJob:
        return self.update_status(
            sync_job,
            status="failed",
            finished_at=datetime.now(timezone.utc),
            error_json=error_json,
        )
