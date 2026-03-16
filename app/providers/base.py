from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field


class ProviderName(str, Enum):
    YOUTUBE = "youtube"
    YANDEX = "yandex"


class ProviderEntityKind(str, Enum):
    ARTIST = "artist"
    RELEASE = "release"
    TRACK = "track"


class ProviderEntityBase(BaseModel):
    provider: ProviderName
    provider_id: str
    url: Optional[str] = None
    raw_json: dict[str, Any] = Field(default_factory=dict)


class ProviderArtist(ProviderEntityBase):
    kind: ProviderEntityKind = ProviderEntityKind.ARTIST
    name: str
    display_norm: str
    match_norm: str
    aliases: list[str] = Field(default_factory=list)
    alias_match_norms: list[str] = Field(default_factory=list)


class ProviderRelease(ProviderEntityBase):
    kind: ProviderEntityKind = ProviderEntityKind.RELEASE
    title: str
    display_norm: str
    match_norm: str
    artist_names: list[str] = Field(default_factory=list)
    artist_match_norms: list[str] = Field(default_factory=list)
    release_type: Optional[str] = None
    release_year: Optional[int] = None
    version_tags_json: list[str] = Field(default_factory=list)
    track_count: Optional[int] = None


class ProviderTrack(ProviderEntityBase):
    kind: ProviderEntityKind = ProviderEntityKind.TRACK
    title: str
    display_norm: str
    match_norm: str
    artist_names: list[str] = Field(default_factory=list)
    artist_match_norms: list[str] = Field(default_factory=list)
    duration_ms: Optional[int] = None
    version_tags_json: list[str] = Field(default_factory=list)
    release_title: Optional[str] = None
    release_match_norm: Optional[str] = None
    track_number: Optional[int] = None


ProviderEntity = Union[ProviderArtist, ProviderRelease, ProviderTrack]


class ProviderSearchHit(BaseModel):
    kind: ProviderEntityKind
    entity: ProviderEntity


class ProviderSearchResult(BaseModel):
    query: str
    items: list[ProviderSearchHit] = Field(default_factory=list)


class MusicProvider(ABC):
    provider_name: ProviderName

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        limit: int,
        kind: Optional[ProviderEntityKind] = None,
    ) -> ProviderSearchResult:
        raise NotImplementedError

    @abstractmethod
    def get_artist(self, provider_id: str) -> ProviderArtist:
        raise NotImplementedError

    @abstractmethod
    def get_release(self, provider_id: str) -> ProviderRelease:
        raise NotImplementedError

    @abstractmethod
    def get_track(self, provider_id: str) -> ProviderTrack:
        raise NotImplementedError
