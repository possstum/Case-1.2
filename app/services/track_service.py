from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas.entities import (
    ExplainabilityPayload,
    LinkedPlatformEntityPayload,
    RelatedArtistPayload,
    RelatedReleasePayload,
    TrackDetailResponse,
)
from app.core.errors import NotFoundError
from app.db.models import LinkTrack, ReleaseTrack, Track, TrackArtist
from app.providers import ProviderName


class TrackService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_track(self, track_id: int) -> TrackDetailResponse:
        track = self.get_track_model(track_id)
        platforms = self._build_platform_map(track)
        missing_platforms = [name for name, payload in platforms.items() if payload is None]
        return TrackDetailResponse(
            id=track.id,
            title=track.title,
            display_norm=track.display_norm,
            match_norm=track.match_norm,
            duration_ms=track.duration_ms,
            version_tags_json=track.version_tags_json,
            metadata_json=track.metadata_json,
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
                    track.artists,
                    key=lambda item: (item.position, item.artist.display_name.casefold()),
                )
            ],
            releases=[
                RelatedReleasePayload(
                    release_id=release_track.release.id,
                    title=release_track.release.title,
                    release_type=release_track.release.release_type,
                    release_year=release_track.release.release_year,
                    position=release_track.position,
                    disc_number=release_track.disc_number,
                    track_number=release_track.track_number,
                )
                for release_track in sorted(
                    track.releases,
                    key=lambda item: (item.position, item.release.title.casefold()),
                )
            ],
            platforms=platforms,
        )

    def get_track_model(self, track_id: int) -> Track:
        statement = (
            select(Track)
            .options(
                selectinload(Track.artists).selectinload(TrackArtist.artist),
                selectinload(Track.releases).selectinload(ReleaseTrack.release),
                selectinload(Track.platform_links).selectinload(LinkTrack.platform_track),
            )
            .where(Track.id == track_id)
        )
        track = self.session.scalar(statement)
        if track is None:
            raise NotFoundError(f"track {track_id} not found")
        return track

    def _build_platform_map(self, track: Track) -> dict[str, LinkedPlatformEntityPayload | None]:
        platforms: dict[str, LinkedPlatformEntityPayload | None] = {
            ProviderName.YOUTUBE.value: None,
            ProviderName.YANDEX.value: None,
        }
        for link in track.platform_links:
            platform_track = link.platform_track
            raw_json = platform_track.raw_json
            platforms[platform_track.platform] = LinkedPlatformEntityPayload(
                provider=platform_track.platform,
                provider_id=platform_track.platform_id,
                kind="track",
                label=platform_track.title,
                display_norm=platform_track.display_norm,
                match_norm=platform_track.match_norm,
                url=raw_json.get("url"),
                artist_names=list(raw_json.get("artist_names", [])),
                duration_ms=platform_track.duration_ms,
                version_tags_json=platform_track.version_tags_json,
                raw_json=raw_json,
                fetched_at=self._coerce_aware(platform_track.fetched_at),
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
