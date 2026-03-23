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
    release_credits: Mapped[list["PlatformReleaseArtist"]] = relationship(
        back_populates="platform_artist",
        cascade="all, delete-orphan",
    )
    track_credits: Mapped[list["PlatformTrackArtist"]] = relationship(
        back_populates="platform_artist",
        cascade="all, delete-orphan",
    )
    catalog_list_memberships: Mapped[list["PlatformCatalogListItem"]] = relationship(
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
    release_type_source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    release_type_confidence: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
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
    artists: Mapped[list["PlatformReleaseArtist"]] = relationship(
        back_populates="platform_release",
        cascade="all, delete-orphan",
    )
    catalog_list_memberships: Mapped[list["PlatformCatalogListItem"]] = relationship(
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
    artists: Mapped[list["PlatformTrackArtist"]] = relationship(
        back_populates="platform_track",
        cascade="all, delete-orphan",
    )
    catalog_list_memberships: Mapped[list["PlatformCatalogListItem"]] = relationship(
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


class PlatformReleaseArtist(TimestampMixin, Base):
    __tablename__ = "platform_release_artists"
    __table_args__ = (
        UniqueConstraint(
            "platform_release_id",
            "platform_artist_id",
            "role",
            "position",
            name="uq_platform_release_artists_release_artist_role_position",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform_release_id: Mapped[int] = mapped_column(
        ForeignKey("platform_releases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform_artist_id: Mapped[int] = mapped_column(
        ForeignKey("platform_artists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="primary")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    platform_release: Mapped["PlatformRelease"] = relationship(back_populates="artists")
    platform_artist: Mapped["PlatformArtist"] = relationship(back_populates="release_credits")


class PlatformTrackArtist(TimestampMixin, Base):
    __tablename__ = "platform_track_artists"
    __table_args__ = (
        UniqueConstraint(
            "platform_track_id",
            "platform_artist_id",
            "role",
            "position",
            name="uq_platform_track_artists_track_artist_role_position",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform_track_id: Mapped[int] = mapped_column(
        ForeignKey("platform_tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform_artist_id: Mapped[int] = mapped_column(
        ForeignKey("platform_artists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="primary")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    platform_track: Mapped["PlatformTrack"] = relationship(back_populates="artists")
    platform_artist: Mapped["PlatformArtist"] = relationship(back_populates="track_credits")


class PlatformCatalogList(TimestampMixin, Base):
    __tablename__ = "platform_catalog_lists"
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "owner_kind",
            "owner_platform_id",
            "list_kind",
            "source_endpoint",
            "page",
            name="uq_platform_catalog_lists_owner_kind_source_page",
        ),
        Index(
            "ix_platform_catalog_lists_owner_kind",
            "platform",
            "owner_kind",
            "owner_platform_id",
            "list_kind",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    owner_platform_id: Mapped[str] = mapped_column(String(255), nullable=False)
    list_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    source_endpoint: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    page: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    page_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_items: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.current_timestamp(),
    )

    items: Mapped[list["PlatformCatalogListItem"]] = relationship(
        back_populates="catalog_list",
        cascade="all, delete-orphan",
    )


class PlatformCatalogListItem(TimestampMixin, Base):
    __tablename__ = "platform_catalog_list_items"
    __table_args__ = (
        UniqueConstraint(
            "catalog_list_id",
            "position",
            name="uq_platform_catalog_list_items_catalog_list_position",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    catalog_list_id: Mapped[int] = mapped_column(
        ForeignKey("platform_catalog_lists.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    item_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    platform_artist_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("platform_artists.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    platform_release_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("platform_releases.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    platform_track_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("platform_tracks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    external_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    catalog_list: Mapped["PlatformCatalogList"] = relationship(back_populates="items")
    platform_artist: Mapped[Optional["PlatformArtist"]] = relationship(
        back_populates="catalog_list_memberships",
    )
    platform_release: Mapped[Optional["PlatformRelease"]] = relationship(
        back_populates="catalog_list_memberships",
    )
    platform_track: Mapped[Optional["PlatformTrack"]] = relationship(
        back_populates="catalog_list_memberships",
    )
