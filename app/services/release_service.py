from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas.entities import (
    ExplainabilityPayload,
    LinkedPlatformEntityPayload,
    RelatedArtistPayload,
    RelatedTrackPayload,
    ReleaseDetailResponse,
)
from app.core.errors import NotFoundError
from app.db.models import LinkRelease, Release, ReleaseArtist, ReleaseTrack
from app.providers import ProviderName


class ReleaseService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_release(self, release_id: int) -> ReleaseDetailResponse:
        release = self.get_release_model(release_id)
        platforms = self._build_platform_map(release)
        missing_platforms = [name for name, payload in platforms.items() if payload is None]
        return ReleaseDetailResponse(
            id=release.id,
            title=release.title,
            display_norm=release.display_norm,
            match_norm=release.match_norm,
            release_type=release.release_type,
            release_year=release.release_year,
            version_tags_json=release.version_tags_json,
            metadata_json=release.metadata_json,
            partial=bool(missing_platforms),
            missing_platforms=missing_platforms,
            artists=[
                RelatedArtistPayload(
                    artist_id=credit.artist.id,
                    display_name=credit.artist.display_name,
                    role=credit.role,
                    position=credit.position,
                )
                for credit in sorted(
                    release.artists,
                    key=lambda item: (item.position, item.artist.display_name.casefold()),
                )
            ],
            tracks=[
                RelatedTrackPayload(
                    track_id=release_track.track.id,
                    title=release_track.track.title,
                    duration_ms=release_track.track.duration_ms,
                    position=release_track.position,
                    disc_number=release_track.disc_number,
                    track_number=release_track.track_number,
                )
                for release_track in sorted(
                    release.tracks,
                    key=lambda item: (item.position, item.track.title.casefold()),
                )
            ],
            platforms=platforms,
        )

    def get_release_model(self, release_id: int) -> Release:
        statement = (
            select(Release)
            .options(
                selectinload(Release.artists).selectinload(ReleaseArtist.artist),
                selectinload(Release.tracks).selectinload(ReleaseTrack.track),
                selectinload(Release.platform_links).selectinload(LinkRelease.platform_release),
            )
            .where(Release.id == release_id)
        )
        release = self.session.scalar(statement)
        if release is None:
            raise NotFoundError(f"release {release_id} not found")
        return release

    def _build_platform_map(self, release: Release) -> dict[str, LinkedPlatformEntityPayload | None]:
        platforms: dict[str, LinkedPlatformEntityPayload | None] = {
            ProviderName.YOUTUBE.value: None,
            ProviderName.YANDEX.value: None,
        }
        for link in release.platform_links:
            platform_release = link.platform_release
            raw_json = platform_release.raw_json
            platforms[platform_release.platform] = LinkedPlatformEntityPayload(
                provider=platform_release.platform,
                provider_id=platform_release.platform_id,
                kind="release",
                label=platform_release.title,
                display_norm=platform_release.display_norm,
                match_norm=platform_release.match_norm,
                url=raw_json.get("url"),
                artist_names=list(raw_json.get("artist_names", [])),
                release_year=platform_release.release_year,
                release_type=platform_release.release_type,
                track_count=raw_json.get("track_count"),
                version_tags_json=platform_release.version_tags_json,
                raw_json=raw_json,
                fetched_at=self._coerce_aware(platform_release.fetched_at),
                explainability=ExplainabilityPayload(
                    decision=link.decision,
                    score=link.score,
                    features_json=link.features_json,
                ),
            )
        return platforms

    def _coerce_aware(self, value: datetime | None) -> datetime | None:
        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=timezone.utc)
