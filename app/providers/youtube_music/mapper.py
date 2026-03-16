from __future__ import annotations

from app.providers.base import ProviderArtist, ProviderName, ProviderRelease, ProviderTrack
from app.providers.youtube_music.schemas import (
    YouTubeMusicArtistPayload,
    YouTubeMusicReleasePayload,
    YouTubeMusicTrackPayload,
)
from app.utils.normalization import display_norm, match_norm
from app.utils.version_tags import extract_version_tags


def map_artist(payload: YouTubeMusicArtistPayload) -> ProviderArtist:
    aliases = list(payload.aliases)
    return ProviderArtist(
        provider=ProviderName.YOUTUBE,
        provider_id=payload.id,
        name=payload.name,
        display_norm=display_norm(payload.name),
        match_norm=match_norm(payload.name),
        aliases=aliases,
        alias_match_norms=[match_norm(alias) for alias in aliases],
        url=payload.url,
        raw_json=payload.raw_json or payload.model_dump(mode="json", exclude_none=True),
    )


def map_release(payload: YouTubeMusicReleasePayload) -> ProviderRelease:
    artist_names = list(payload.artists)
    return ProviderRelease(
        provider=ProviderName.YOUTUBE,
        provider_id=payload.id,
        title=payload.title,
        display_norm=display_norm(payload.title),
        match_norm=match_norm(payload.title),
        artist_names=artist_names,
        artist_match_norms=[match_norm(name) for name in artist_names],
        release_type=payload.release_type,
        release_year=payload.year,
        version_tags_json=extract_version_tags(payload.title),
        track_count=payload.track_count,
        url=payload.url,
        raw_json=payload.raw_json or payload.model_dump(mode="json", exclude_none=True),
    )


def map_track(payload: YouTubeMusicTrackPayload) -> ProviderTrack:
    artist_names = list(payload.artists)
    return ProviderTrack(
        provider=ProviderName.YOUTUBE,
        provider_id=payload.id,
        title=payload.title,
        display_norm=display_norm(payload.title),
        match_norm=match_norm(payload.title),
        artist_names=artist_names,
        artist_match_norms=[match_norm(name) for name in artist_names],
        duration_ms=payload.duration_ms,
        version_tags_json=extract_version_tags(payload.title),
        release_title=payload.release_title,
        release_match_norm=match_norm(payload.release_title or "") or None,
        track_number=payload.track_number,
        url=payload.url,
        raw_json=payload.raw_json or payload.model_dump(mode="json", exclude_none=True),
    )
