from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ExplainabilityPayload(BaseModel):
    decision: str
    score: float
    features_json: dict[str, Any] = Field(default_factory=dict)


class LinkedPlatformEntityPayload(BaseModel):
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
    raw_json: dict[str, Any] = Field(default_factory=dict)
    fetched_at: Optional[datetime] = None
    explainability: ExplainabilityPayload


class ArtistAliasPayload(BaseModel):
    alias: str
    display_norm: str
    match_norm: str
    source: Optional[str] = None


class RelatedArtistPayload(BaseModel):
    artist_id: int
    display_name: str
    role: str
    position: int


class RelatedReleasePayload(BaseModel):
    release_id: int
    title: str
    release_type: Optional[str] = None
    release_year: Optional[int] = None
    track_count: Optional[int] = None
    role: Optional[str] = None
    position: int
    available_platforms: list[str] = Field(default_factory=list)
    missing_platforms: list[str] = Field(default_factory=list)
    is_missing_yandex: bool = False
    disc_number: Optional[int] = None
    track_number: Optional[int] = None


class RelatedTrackPayload(BaseModel):
    track_id: int
    title: str
    duration_ms: Optional[int] = None
    role: Optional[str] = None
    position: int
    disc_number: Optional[int] = None
    track_number: Optional[int] = None


class ProviderCatalogSectionItemPayload(BaseModel):
    item_kind: str
    provider_id: Optional[str] = None
    label: str
    subtitle: Optional[str] = None
    url: Optional[str] = None


class ProviderCatalogSectionPayload(BaseModel):
    provider: str
    list_kind: str
    title: str
    total_items: Optional[int] = None
    items: list[ProviderCatalogSectionItemPayload] = Field(default_factory=list)


class MissingOnYandexCandidatePayload(BaseModel):
    provider_id: str
    label: str
    release_type: Optional[str] = None
    release_year: Optional[int] = None
    source_list_kinds: list[str] = Field(default_factory=list)
    url: Optional[str] = None


class MissingOnYandexItemPayload(BaseModel):
    release_id: int
    title: str
    release_type: Optional[str] = None
    release_year: Optional[int] = None
    track_count: Optional[int] = None
    role: Optional[str] = None
    position: int
    status: str
    yandex_candidates: list[MissingOnYandexCandidatePayload] = Field(default_factory=list)


class MissingOnYandexViewPayload(BaseModel):
    total_items: int = 0
    candidate_count: int = 0
    missing_count: int = 0
    items: list[MissingOnYandexItemPayload] = Field(default_factory=list)


class EntityDetailBase(BaseModel):
    id: int
    kind: str
    partial: bool
    missing_platforms: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    platforms: dict[str, Optional[LinkedPlatformEntityPayload]] = Field(default_factory=dict)


class ArtistDetailResponse(EntityDetailBase):
    kind: str = "artist"
    display_name: str
    display_norm: str
    match_norm: str
    country_code: Optional[str] = None
    aliases: list[ArtistAliasPayload] = Field(default_factory=list)
    releases: list[RelatedReleasePayload] = Field(default_factory=list)
    tracks: list[RelatedTrackPayload] = Field(default_factory=list)
    yandex_catalog_sections: list[ProviderCatalogSectionPayload] = Field(default_factory=list)
    missing_on_yandex_view: MissingOnYandexViewPayload = Field(default_factory=MissingOnYandexViewPayload)


class ReleaseDetailResponse(EntityDetailBase):
    kind: str = "release"
    title: str
    display_norm: str
    match_norm: str
    release_type: Optional[str] = None
    release_year: Optional[int] = None
    version_tags_json: list[str] = Field(default_factory=list)
    artists: list[RelatedArtistPayload] = Field(default_factory=list)
    tracks: list[RelatedTrackPayload] = Field(default_factory=list)


class TrackDetailResponse(EntityDetailBase):
    kind: str = "track"
    title: str
    display_norm: str
    match_norm: str
    duration_ms: Optional[int] = None
    version_tags_json: list[str] = Field(default_factory=list)
    artists: list[RelatedArtistPayload] = Field(default_factory=list)
    releases: list[RelatedReleasePayload] = Field(default_factory=list)
