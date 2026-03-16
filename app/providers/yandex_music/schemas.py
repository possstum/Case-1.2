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
    track_number: Optional[int] = None
    url: Optional[str] = None
    raw_json: dict[str, Any] = Field(default_factory=dict)
