from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.canonical import Artist, Release, Track
    from app.db.models.platform import PlatformArtist, PlatformRelease, PlatformTrack


class LinkArtist(TimestampMixin, Base):
    __tablename__ = "links_artist"
    __table_args__ = (
        UniqueConstraint("artist_id", "platform_artist_id", name="uq_links_artist_artist_platform"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    artist_id: Mapped[int] = mapped_column(
        ForeignKey("artists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform_artist_id: Mapped[int] = mapped_column(
        ForeignKey("platform_artists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    features_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    artist: Mapped["Artist"] = relationship(back_populates="platform_links")
    platform_artist: Mapped["PlatformArtist"] = relationship(back_populates="links")


class LinkRelease(TimestampMixin, Base):
    __tablename__ = "links_release"
    __table_args__ = (
        UniqueConstraint(
            "release_id",
            "platform_release_id",
            name="uq_links_release_release_platform",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    release_id: Mapped[int] = mapped_column(
        ForeignKey("releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform_release_id: Mapped[int] = mapped_column(
        ForeignKey("platform_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    features_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    release: Mapped["Release"] = relationship(back_populates="platform_links")
    platform_release: Mapped["PlatformRelease"] = relationship(back_populates="links")


class LinkTrack(TimestampMixin, Base):
    __tablename__ = "links_track"
    __table_args__ = (
        UniqueConstraint("track_id", "platform_track_id", name="uq_links_track_track_platform"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[int] = mapped_column(
        ForeignKey("tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform_track_id: Mapped[int] = mapped_column(
        ForeignKey("platform_tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    features_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    track: Mapped["Track"] = relationship(back_populates="platform_links")
    platform_track: Mapped["PlatformTrack"] = relationship(back_populates="links")
