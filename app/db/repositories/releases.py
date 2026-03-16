from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Artist, Release, ReleaseArtist, ReleaseTrack, Track


class ReleaseRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        title: str,
        display_norm: str,
        match_norm: str,
        release_type: Optional[str] = None,
        release_year: Optional[int] = None,
        version_tags_json: Optional[list[str]] = None,
        metadata_json: Optional[dict[str, Any]] = None,
    ) -> Release:
        release = Release(
            title=title,
            display_norm=display_norm,
            match_norm=match_norm,
            release_type=release_type,
            release_year=release_year,
            version_tags_json=version_tags_json or [],
            metadata_json=metadata_json or {},
        )
        self.session.add(release)
        self.session.flush()
        return release

    def add_artist(
        self,
        *,
        release: Release,
        artist: Artist,
        role: str = "primary",
        position: int = 0,
    ) -> ReleaseArtist:
        credit = ReleaseArtist(
            release=release,
            artist=artist,
            role=role,
            position=position,
        )
        self.session.add(credit)
        self.session.flush()
        return credit

    def add_track(
        self,
        *,
        release: Release,
        track: Track,
        position: int,
        disc_number: int = 1,
        track_number: int = 1,
    ) -> ReleaseTrack:
        release_track = ReleaseTrack(
            release=release,
            track=track,
            position=position,
            disc_number=disc_number,
            track_number=track_number,
        )
        self.session.add(release_track)
        self.session.flush()
        return release_track

    def get(self, release_id: int) -> Optional[Release]:
        statement = (
            select(Release)
            .options(
                selectinload(Release.artists).selectinload(ReleaseArtist.artist),
                selectinload(Release.tracks).selectinload(ReleaseTrack.track),
            )
            .where(Release.id == release_id)
        )
        return self.session.scalar(statement)
