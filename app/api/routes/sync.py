from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, status

from app.api.deps import enforce_sync_rate_limit, get_sync_service
from app.api.schemas.sync import SyncEnqueueResponse
from app.services.sync_service import SyncService

router = APIRouter()


@router.post(
    "/sync/{kind}/{target_id}",
    response_model=SyncEnqueueResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(enforce_sync_rate_limit)],
)
def enqueue_sync(
    kind: Literal["artist", "release", "track"],
    target_id: int,
    sync_service: SyncService = Depends(get_sync_service),
) -> SyncEnqueueResponse:
    return sync_service.enqueue(kind=kind, target_id=target_id)
