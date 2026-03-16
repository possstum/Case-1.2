from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import enforce_search_rate_limit, get_search_service
from app.api.schemas.search import SearchResponse
from app.services.search_service import SearchService

router = APIRouter()


@router.get("/search", response_model=SearchResponse, dependencies=[Depends(enforce_search_rate_limit)])
def search(
    q: str = Query(..., min_length=1),
    kind: Optional[str] = Query(default=None, pattern="^(artist|release|track)$"),
    limit: Optional[int] = Query(default=None, ge=1),
    search_service: SearchService = Depends(get_search_service),
) -> SearchResponse:
    return search_service.search(query=q, kind=kind, limit=limit)
