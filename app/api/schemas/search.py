from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SearchCacheMetadata(BaseModel):
    status: str
    hit_count: int = 0
    last_refreshed_at: Optional[datetime] = None
    stale_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    refresh_queued: bool = False
    refresh_job_id: Optional[str] = None


class SearchPlatformEntityPayload(BaseModel):
    provider: str
    provider_id: str
    kind: str
    label: str
    display_norm: str
    match_norm: str
    url: Optional[str] = None
    artist_names: list[str] = Field(default_factory=list)
    release_year: Optional[int] = None
    release_type: Optional[str] = None
    duration_ms: Optional[int] = None
    track_count: Optional[int] = None
    version_tags_json: list[str] = Field(default_factory=list)


class SearchResultItemPayload(BaseModel):
    kind: str
    canonical_id: Optional[int] = None
    decision: str
    score: float
    features_json: dict[str, Any] = Field(default_factory=dict)
    platforms: dict[str, Optional[SearchPlatformEntityPayload]] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    normalized_query: str
    kind: Optional[str] = None
    partial: bool
    missing_platforms: list[str] = Field(default_factory=list)
    cache: SearchCacheMetadata
    results: list[SearchResultItemPayload] = Field(default_factory=list)
