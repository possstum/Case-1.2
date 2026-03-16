from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_release_service
from app.api.schemas.entities import ReleaseDetailResponse
from app.services.release_service import ReleaseService

router = APIRouter()


@router.get("/releases/{release_id}", response_model=ReleaseDetailResponse)
def get_release(
    release_id: int,
    release_service: ReleaseService = Depends(get_release_service),
) -> ReleaseDetailResponse:
    return release_service.get_release(release_id)
