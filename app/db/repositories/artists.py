from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Artist, ArtistAlias


class ArtistRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        display_name: str,
        display_norm: str,
        match_norm: str,
        country_code: Optional[str] = None,
        metadata_json: Optional[dict[str, Any]] = None,
        aliases: Optional[Sequence[dict[str, Any]]] = None,
    ) -> Artist:
        artist = Artist(
            display_name=display_name,
            display_norm=display_norm,
            match_norm=match_norm,
            country_code=country_code,
            metadata_json=metadata_json or {},
        )
        self.session.add(artist)
        self.session.flush()

        for alias_payload in aliases or []:
            self.add_alias(artist=artist, **alias_payload)

        self.session.flush()
        return artist

    def add_alias(
        self,
        *,
        artist: Artist,
        alias: str,
        display_norm: str,
        match_norm: str,
        source: Optional[str] = None,
    ) -> ArtistAlias:
        artist_alias = ArtistAlias(
            artist=artist,
            alias=alias,
            display_norm=display_norm,
            match_norm=match_norm,
            source=source,
        )
        self.session.add(artist_alias)
        self.session.flush()
        return artist_alias

    def get(self, artist_id: int) -> Optional[Artist]:
        statement = (
            select(Artist)
            .options(selectinload(Artist.aliases))
            .where(Artist.id == artist_id)
        )
        return self.session.scalar(statement)

    def get_by_match_norm(self, match_norm: str) -> list[Artist]:
        statement = select(Artist).where(Artist.match_norm == match_norm)
        return list(self.session.scalars(statement))
