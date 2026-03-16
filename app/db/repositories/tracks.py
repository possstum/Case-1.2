from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Artist, Track, TrackArtist


class TrackRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        title: str,
        display_norm: str,
        match_norm: str,
        duration_ms: Optional[int] = None,
        version_tags_json: Optional[list[str]] = None,
        metadata_json: Optional[dict[str, Any]] = None,
    ) -> Track:
        track = Track(
            title=title,
            display_norm=display_norm,
            match_norm=match_norm,
            duration_ms=duration_ms,
            version_tags_json=version_tags_json or [],
            metadata_json=metadata_json or {},
        )
        self.session.add(track)
        self.session.flush()
        return track

    def add_artist(
        self,
        *,
        track: Track,
        artist: Artist,
        role: str = "primary",
        position: int = 0,
    ) -> TrackArtist:
        credit = TrackArtist(
            track=track,
            artist=artist,
            role=role,
            position=position,
        )
        self.session.add(credit)
        self.session.flush()
        return credit

    def get(self, track_id: int) -> Optional[Track]:
        statement = (
            select(Track)
            .options(selectinload(Track.artists).selectinload(TrackArtist.artist))
            .where(Track.id == track_id)
        )
        return self.session.scalar(statement)
