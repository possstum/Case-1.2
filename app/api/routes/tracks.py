from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_track_service
from app.api.schemas.entities import TrackDetailResponse
from app.services.track_service import TrackService

router = APIRouter()


@router.get("/tracks/{track_id}", response_model=TrackDetailResponse)
def get_track(
    track_id: int,
    track_service: TrackService = Depends(get_track_service),
) -> TrackDetailResponse:
    return track_service.get_track(track_id)
