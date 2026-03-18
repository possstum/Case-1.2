from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class YandexMusicArtistPayload(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    url: Optional[str] = None
    raw_json: dict[str, Any] = Field(default_factory=dict)


class YandexMusicReleasePayload(BaseModel):
    id: str
    title: str
    artists: list[str] = Field(default_factory=list)
    release_type: Optional[str] = None
    year: Optional[int] = None
    track_count: Optional[int] = None
    url: Optional[str] = None
    raw_json: dict[str, Any] = Field(default_factory=dict)


class YandexMusicTrackPayload(BaseModel):
    id: str
    title: str
    artists: list[str] = Field(default_factory=list)
    duration_ms: Optional[int] = None
    release_title: Optional[str] = None
    disc_number: Optional[int] = None
    track_number: Optional[int] = None
    url: Optional[str] = None
    raw_json: dict[str, Any] = Field(default_factory=dict)


class YandexMusicPagerPayload(BaseModel):
    page: Optional[int] = None
    per_page: Optional[int] = None
    total: Optional[int] = None


class YandexMusicCollectionItemPayload(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    raw_json: dict[str, Any] = Field(default_factory=dict)


class YandexMusicArtistDetailPayload(BaseModel):
    artist: YandexMusicArtistPayload
    albums: list[YandexMusicReleasePayload] = Field(default_factory=list)
    also_albums: list[YandexMusicReleasePayload] = Field(default_factory=list)
    popular_tracks: list[YandexMusicTrackPayload] = Field(default_factory=list)
    similar_artists: list[YandexMusicArtistPayload] = Field(default_factory=list)
    last_releases: list[YandexMusicReleasePayload] = Field(default_factory=list)
    videos: list[YandexMusicCollectionItemPayload] = Field(default_factory=list)
    clips: list[YandexMusicCollectionItemPayload] = Field(default_factory=list)
    vinyls: list[YandexMusicCollectionItemPayload] = Field(default_factory=list)
    raw_json: dict[str, Any] = Field(default_factory=dict)


class YandexMusicArtistBriefInfoPayload(YandexMusicArtistDetailPayload):
    stats: dict[str, Any] = Field(default_factory=dict)
    playlist_ids: list[str] = Field(default_factory=list)
    playlists: list[YandexMusicCollectionItemPayload] = Field(default_factory=list)
    links: list[YandexMusicCollectionItemPayload] = Field(default_factory=list)
    has_trailer: Optional[bool] = None


class YandexMusicArtistDirectAlbumsPayload(BaseModel):
    artist_id: str
    pager: Optional[YandexMusicPagerPayload] = None
    albums: list[YandexMusicReleasePayload] = Field(default_factory=list)
    raw_json: dict[str, Any] = Field(default_factory=dict)


class YandexMusicArtistTracksPayload(BaseModel):
    artist_id: str
    pager: Optional[YandexMusicPagerPayload] = None
    tracks: list[YandexMusicTrackPayload] = Field(default_factory=list)
    raw_json: dict[str, Any] = Field(default_factory=dict)


class YandexMusicAlbumWithTracksPayload(BaseModel):
    release: YandexMusicReleasePayload
    pager: Optional[YandexMusicPagerPayload] = None
    volumes: list[list[YandexMusicTrackPayload]] = Field(default_factory=list)
    raw_json: dict[str, Any] = Field(default_factory=dict)
