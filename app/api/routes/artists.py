from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_artist_service
from app.api.schemas.entities import ArtistDetailResponse
from app.services.artist_service import ArtistService

router = APIRouter()


@router.get("/artists/{artist_id}", response_model=ArtistDetailResponse)
def get_artist(
    artist_id: int,
    artist_service: ArtistService = Depends(get_artist_service),
) -> ArtistDetailResponse:
    return artist_service.get_artist(artist_id)
