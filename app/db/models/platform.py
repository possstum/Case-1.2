from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, utcnow

if TYPE_CHECKING:
    from app.db.models.links import LinkArtist, LinkRelease, LinkTrack


class PlatformArtist(TimestampMixin, Base):
    __tablename__ = "platform_artists"
    __table_args__ = (
        UniqueConstraint("platform", "platform_id", name="uq_platform_artists_platform_platform_id"),
        Index("ix_platform_artists_match_norm", "platform", "match_norm"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    platform_id: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    display_norm: Mapped[str] = mapped_column(String(512), nullable=False)
    match_norm: Mapped[str] = mapped_column(String(512), nullable=False)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.current_timestamp(),
    )

    links: Mapped[list["LinkArtist"]] = relationship(
        back_populates="platform_artist",
        cascade="all, delete-orphan",
    )


class PlatformRelease(TimestampMixin, Base):
    __tablename__ = "platform_releases"
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "platform_id",
            name="uq_platform_releases_platform_platform_id",
        ),
        Index("ix_platform_releases_match_norm", "platform", "match_norm"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    platform_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    display_norm: Mapped[str] = mapped_column(String(512), nullable=False)
    match_norm: Mapped[str] = mapped_column(String(512), nullable=False)
    release_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    release_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    version_tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.current_timestamp(),
    )

    tracks: Mapped[list["PlatformReleaseTrack"]] = relationship(
        back_populates="platform_release",
        cascade="all, delete-orphan",
    )
    links: Mapped[list["LinkRelease"]] = relationship(
        back_populates="platform_release",
        cascade="all, delete-orphan",
    )


class PlatformTrack(TimestampMixin, Base):
    __tablename__ = "platform_tracks"
    __table_args__ = (
        UniqueConstraint("platform", "platform_id", name="uq_platform_tracks_platform_platform_id"),
        Index("ix_platform_tracks_match_norm", "platform", "match_norm"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    platform_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    display_norm: Mapped[str] = mapped_column(String(512), nullable=False)
    match_norm: Mapped[str] = mapped_column(String(512), nullable=False)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    version_tags_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.current_timestamp(),
    )

    releases: Mapped[list["PlatformReleaseTrack"]] = relationship(
        back_populates="platform_track",
        cascade="all, delete-orphan",
    )
    links: Mapped[list["LinkTrack"]] = relationship(
        back_populates="platform_track",
        cascade="all, delete-orphan",
    )


class PlatformReleaseTrack(TimestampMixin, Base):
    __tablename__ = "platform_release_tracks"
    __table_args__ = (
        UniqueConstraint(
            "platform_release_id",
            "position",
            name="uq_platform_release_tracks_release_position",
        ),
        UniqueConstraint(
            "platform_release_id",
            "disc_number",
            "track_number",
            name="uq_platform_release_tracks_release_disc_track",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform_release_id: Mapped[int] = mapped_column(
        ForeignKey("platform_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform_track_id: Mapped[int] = mapped_column(
        ForeignKey("platform_tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    disc_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    track_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    platform_release: Mapped["PlatformRelease"] = relationship(back_populates="tracks")
    platform_track: Mapped["PlatformTrack"] = relationship(back_populates="releases")
