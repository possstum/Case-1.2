from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas.entities import (
    ArtistAliasPayload,
    ArtistDetailResponse,
    ExplainabilityPayload,
    LinkedPlatformEntityPayload,
    RelatedReleasePayload,
    RelatedTrackPayload,
)
from app.core.errors import NotFoundError
from app.db.models import Artist, LinkArtist, ReleaseArtist, TrackArtist
from app.providers import ProviderName


class ArtistService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_artist(self, artist_id: int) -> ArtistDetailResponse:
        artist = self.get_artist_model(artist_id)
        platforms = self._build_platform_map(artist)
        missing_platforms = [name for name, payload in platforms.items() if payload is None]
        return ArtistDetailResponse(
            id=artist.id,
            display_name=artist.display_name,
            display_norm=artist.display_norm,
            match_norm=artist.match_norm,
            country_code=artist.country_code,
            metadata_json=artist.metadata_json,
            partial=bool(missing_platforms),
            missing_platforms=missing_platforms,
            aliases=[
                ArtistAliasPayload(
                    alias=alias.alias,
                    display_norm=alias.display_norm,
                    match_norm=alias.match_norm,
                    source=alias.source,
                )
                for alias in sorted(artist.aliases, key=lambda item: item.alias.casefold())
            ],
            releases=[
                RelatedReleasePayload(
                    release_id=credit.release.id,
                    title=credit.release.title,
                    release_type=credit.release.release_type,
                    release_year=credit.release.release_year,
                    role=credit.role,
                    position=credit.position,
                )
                for credit in sorted(
                    artist.release_credits,
                    key=lambda item: (item.position, item.release.title.casefold()),
                )
            ],
            tracks=[
                RelatedTrackPayload(
                    track_id=credit.track.id,
                    title=credit.track.title,
                    duration_ms=credit.track.duration_ms,
                    role=credit.role,
                    position=credit.position,
                )
                for credit in sorted(
                    artist.track_credits,
                    key=lambda item: (item.position, item.track.title.casefold()),
                )
            ],
            platforms=platforms,
        )

    def get_artist_model(self, artist_id: int) -> Artist:
        statement = (
            select(Artist)
            .options(
                selectinload(Artist.aliases),
                selectinload(Artist.release_credits).selectinload(ReleaseArtist.release),
                selectinload(Artist.track_credits).selectinload(TrackArtist.track),
                selectinload(Artist.platform_links).selectinload(LinkArtist.platform_artist),
            )
            .where(Artist.id == artist_id)
        )
        artist = self.session.scalar(statement)
        if artist is None:
            raise NotFoundError(f"artist {artist_id} not found")
        return artist

    def _build_platform_map(self, artist: Artist) -> dict[str, LinkedPlatformEntityPayload | None]:
        platforms: dict[str, LinkedPlatformEntityPayload | None] = {
            ProviderName.YOUTUBE.value: None,
            ProviderName.YANDEX.value: None,
        }
        for link in artist.platform_links:
            platform_artist = link.platform_artist
            platforms[platform_artist.platform] = LinkedPlatformEntityPayload(
                provider=platform_artist.platform,
                provider_id=platform_artist.platform_id,
                kind="artist",
                label=platform_artist.display_name,
                display_norm=platform_artist.display_norm,
                match_norm=platform_artist.match_norm,
                url=platform_artist.raw_json.get("url"),
                raw_json=platform_artist.raw_json,
                fetched_at=self._coerce_aware(platform_artist.fetched_at),
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
