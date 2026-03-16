from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_sync_service
from app.api.schemas.jobs import SyncJobResponse
from app.services.sync_service import SyncService

router = APIRouter()


@router.get("/jobs/{job_id}", response_model=SyncJobResponse)
def get_job(
    job_id: str,
    sync_service: SyncService = Depends(get_sync_service),
) -> SyncJobResponse:
    return sync_service.get_job(job_id)
