from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.links import LinkArtist, LinkRelease, LinkTrack


class Artist(TimestampMixin, Base):
    __tablename__ = "artists"
    __table_args__ = (
        Index("ix_artists_display_norm", "display_norm"),
        Index("ix_artists_match_norm", "match_norm"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    display_norm: Mapped[str] = mapped_column(String(512), nullable=False)
    match_norm: Mapped[str] = mapped_column(String(512), nullable=False)
    country_code: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    aliases: Mapped[list["ArtistAlias"]] = relationship(
        back_populates="artist",
        cascade="all, delete-orphan",
    )
    release_credits: Mapped[list["ReleaseArtist"]] = relationship(
        back_populates="artist",
        cascade="all, delete-orphan",
    )
    track_credits: Mapped[list["TrackArtist"]] = relationship(
        back_populates="artist",
        cascade="all, delete-orphan",
    )
    platform_links: Mapped[list["LinkArtist"]] = relationship(
        back_populates="artist",
        cascade="all, delete-orphan",
    )


class ArtistAlias(TimestampMixin, Base):
    __tablename__ = "artist_aliases"
    __table_args__ = (
        UniqueConstraint("artist_id", "match_norm", name="uq_artist_aliases_artist_match_norm"),
        Index("ix_artist_aliases_match_norm", "match_norm"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artist_id: Mapped[int] = mapped_column(
        ForeignKey("artists.id", ondelete="CASCADE"),
        nullable=False,
    )
    alias: Mapped[str] = mapped_column(String(512), nullable=False)
    display_norm: Mapped[str] = mapped_column(String(512), nullable=False)
    match_norm: Mapped[str] = mapped_column(String(512), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    artist: Mapped["Artist"] = relationship(back_populates="aliases")


class Release(TimestampMixin, Base):
    __tablename__ = "releases"
    __table_args__ = (
        Index("ix_releases_display_norm", "display_norm"),
        Index("ix_releases_match_norm", "match_norm"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    display_norm: Mapped[str] = mapped_column(String(512), nullable=False)
    match_norm: Mapped[str] = mapped_column(String(512), nullable=False)
    release_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    release_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    version_tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    artists: Mapped[list["ReleaseArtist"]] = relationship(
        back_populates="release",
        cascade="all, delete-orphan",
    )
    tracks: Mapped[list["ReleaseTrack"]] = relationship(
        back_populates="release",
        cascade="all, delete-orphan",
    )
    platform_links: Mapped[list["LinkRelease"]] = relationship(
        back_populates="release",
        cascade="all, delete-orphan",
    )


class Track(TimestampMixin, Base):
    __tablename__ = "tracks"
    __table_args__ = (
        Index("ix_tracks_display_norm", "display_norm"),
        Index("ix_tracks_match_norm", "match_norm"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    display_norm: Mapped[str] = mapped_column(String(512), nullable=False)
    match_norm: Mapped[str] = mapped_column(String(512), nullable=False)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    version_tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    artists: Mapped[list["TrackArtist"]] = relationship(
        back_populates="track",
        cascade="all, delete-orphan",
    )
    releases: Mapped[list["ReleaseTrack"]] = relationship(
        back_populates="track",
        cascade="all, delete-orphan",
    )
    platform_links: Mapped[list["LinkTrack"]] = relationship(
        back_populates="track",
        cascade="all, delete-orphan",
    )


class ReleaseArtist(TimestampMixin, Base):
    __tablename__ = "release_artists"
    __table_args__ = (
        UniqueConstraint(
            "release_id",
            "artist_id",
            "role",
            "position",
            name="uq_release_artists_release_artist_role_position",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    release_id: Mapped[int] = mapped_column(
        ForeignKey("releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artist_id: Mapped[int] = mapped_column(
        ForeignKey("artists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="primary")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    release: Mapped["Release"] = relationship(back_populates="artists")
    artist: Mapped["Artist"] = relationship(back_populates="release_credits")


class TrackArtist(TimestampMixin, Base):
    __tablename__ = "track_artists"
    __table_args__ = (
        UniqueConstraint(
            "track_id",
            "artist_id",
            "role",
            "position",
            name="uq_track_artists_track_artist_role_position",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[int] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artist_id: Mapped[int] = mapped_column(
        ForeignKey("artists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="primary")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    track: Mapped["Track"] = relationship(back_populates="artists")
    artist: Mapped["Artist"] = relationship(back_populates="track_credits")


class ReleaseTrack(TimestampMixin, Base):
    __tablename__ = "release_tracks"
    __table_args__ = (
        UniqueConstraint("release_id", "position", name="uq_release_tracks_release_position"),
        UniqueConstraint(
            "release_id",
            "disc_number",
            "track_number",
            name="uq_release_tracks_release_disc_track",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    release_id: Mapped[int] = mapped_column(
        ForeignKey("releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    track_id: Mapped[int] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    disc_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    track_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    release: Mapped["Release"] = relationship(back_populates="tracks")
    track: Mapped["Track"] = relationship(back_populates="releases")
