from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Artist,
    LinkArtist,
    LinkRelease,
    LinkTrack,
    PlatformArtist,
    PlatformRelease,
    PlatformTrack,
    Release,
    Track,
)
from app.db.models.mixins import utcnow
from app.providers.base import ProviderArtist, ProviderEntity, ProviderRelease, ProviderTrack


class LinkService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def persist_platform_entity(
        self,
        entity: ProviderEntity,
    ) -> PlatformArtist | PlatformRelease | PlatformTrack:
        if isinstance(entity, ProviderArtist):
            return self._upsert_platform_artist(entity)
        if isinstance(entity, ProviderRelease):
            return self._upsert_platform_release(entity)
        return self._upsert_platform_track(entity)

    def persist_match(
        self,
        left_entity: ProviderEntity,
        right_entity: ProviderEntity,
        *,
        decision: str,
        score: float,
        features_json: dict[str, Any],
    ) -> int:
        left_platform = self.persist_platform_entity(left_entity)
        right_platform = self.persist_platform_entity(right_entity)

        existing_canonical_id = self._resolve_existing_canonical_id(left_entity, left_platform) or self._resolve_existing_canonical_id(
            right_entity,
            right_platform,
        )
        canonical_id = existing_canonical_id or self._create_canonical_entity(left_entity)

        self._upsert_link(
            left_entity,
            canonical_id=canonical_id,
            platform_row=left_platform,
            decision=decision,
            score=score,
            features_json=features_json,
        )
        self._upsert_link(
            right_entity,
            canonical_id=canonical_id,
            platform_row=right_platform,
            decision=decision,
            score=score,
            features_json=features_json,
        )
        self.session.flush()
        return canonical_id

    def _resolve_existing_canonical_id(
        self,
        entity: ProviderEntity,
        platform_row: PlatformArtist | PlatformRelease | PlatformTrack,
    ) -> Optional[int]:
        if isinstance(entity, ProviderArtist):
            statement = select(LinkArtist.artist_id).where(LinkArtist.platform_artist_id == platform_row.id)
        elif isinstance(entity, ProviderRelease):
            statement = select(LinkRelease.release_id).where(LinkRelease.platform_release_id == platform_row.id)
        else:
            statement = select(LinkTrack.track_id).where(LinkTrack.platform_track_id == platform_row.id)
        return self.session.scalar(statement)

    def _create_canonical_entity(self, entity: ProviderEntity) -> int:
        if isinstance(entity, ProviderArtist):
            row = Artist(
                display_name=entity.name,
                display_norm=entity.display_norm,
                match_norm=entity.match_norm,
                metadata_json={},
            )
        elif isinstance(entity, ProviderRelease):
            row = Release(
                title=entity.title,
                display_norm=entity.display_norm,
                match_norm=entity.match_norm,
                release_type=entity.release_type,
                release_year=entity.release_year,
                version_tags_json=entity.version_tags_json,
                metadata_json={},
            )
        else:
            row = Track(
                title=entity.title,
                display_norm=entity.display_norm,
                match_norm=entity.match_norm,
                duration_ms=entity.duration_ms,
                version_tags_json=entity.version_tags_json,
                metadata_json={},
            )

        self.session.add(row)
        self.session.flush()
        return row.id

    def _upsert_platform_artist(self, entity: ProviderArtist) -> PlatformArtist:
        statement = select(PlatformArtist).where(
            PlatformArtist.platform == entity.provider.value,
            PlatformArtist.platform_id == entity.provider_id,
        )
        row = self.session.scalar(statement)
        if row is None:
            row = PlatformArtist(
                platform=entity.provider.value,
                platform_id=entity.provider_id,
                display_name=entity.name,
                display_norm=entity.display_norm,
                match_norm=entity.match_norm,
                raw_json=entity.raw_json,
            )
            self.session.add(row)
        else:
            row.display_name = entity.name
            row.display_norm = entity.display_norm
            row.match_norm = entity.match_norm
            row.raw_json = entity.raw_json
            row.fetched_at = utcnow()
        self.session.flush()
        return row

    def _upsert_platform_release(self, entity: ProviderRelease) -> PlatformRelease:
        statement = select(PlatformRelease).where(
            PlatformRelease.platform == entity.provider.value,
            PlatformRelease.platform_id == entity.provider_id,
        )
        row = self.session.scalar(statement)
        if row is None:
            row = PlatformRelease(
                platform=entity.provider.value,
                platform_id=entity.provider_id,
                title=entity.title,
                display_norm=entity.display_norm,
                match_norm=entity.match_norm,
                release_type=entity.release_type,
                release_year=entity.release_year,
                version_tags_json=entity.version_tags_json,
                raw_json=entity.raw_json,
            )
            self.session.add(row)
        else:
            row.title = entity.title
            row.display_norm = entity.display_norm
            row.match_norm = entity.match_norm
            row.release_type = entity.release_type
            row.release_year = entity.release_year
            row.version_tags_json = entity.version_tags_json
            row.raw_json = entity.raw_json
            row.fetched_at = utcnow()
        self.session.flush()
        return row

    def _upsert_platform_track(self, entity: ProviderTrack) -> PlatformTrack:
        statement = select(PlatformTrack).where(
            PlatformTrack.platform == entity.provider.value,
            PlatformTrack.platform_id == entity.provider_id,
        )
        row = self.session.scalar(statement)
        if row is None:
            row = PlatformTrack(
                platform=entity.provider.value,
                platform_id=entity.provider_id,
                title=entity.title,
                display_norm=entity.display_norm,
                match_norm=entity.match_norm,
                duration_ms=entity.duration_ms,
                version_tags_json=entity.version_tags_json,
                raw_json=entity.raw_json,
            )
            self.session.add(row)
        else:
            row.title = entity.title
            row.display_norm = entity.display_norm
            row.match_norm = entity.match_norm
            row.duration_ms = entity.duration_ms
            row.version_tags_json = entity.version_tags_json
            row.raw_json = entity.raw_json
            row.fetched_at = utcnow()
        self.session.flush()
        return row

    def _upsert_link(
        self,
        entity: ProviderEntity,
        *,
        canonical_id: int,
        platform_row: PlatformArtist | PlatformRelease | PlatformTrack,
        decision: str,
        score: float,
        features_json: dict[str, Any],
    ) -> LinkArtist | LinkRelease | LinkTrack:
        if isinstance(entity, ProviderArtist):
            statement = select(LinkArtist).where(
                LinkArtist.artist_id == canonical_id,
                LinkArtist.platform_artist_id == platform_row.id,
            )
            row = self.session.scalar(statement)
            if row is None:
                row = LinkArtist(
                    artist_id=canonical_id,
                    platform_artist_id=platform_row.id,
                    decision=decision,
                    score=score,
                    features_json=features_json,
                )
                self.session.add(row)
            else:
                row.decision = decision
                row.score = score
                row.features_json = features_json
            return row

        if isinstance(entity, ProviderRelease):
            statement = select(LinkRelease).where(
                LinkRelease.release_id == canonical_id,
                LinkRelease.platform_release_id == platform_row.id,
            )
            row = self.session.scalar(statement)
            if row is None:
                row = LinkRelease(
                    release_id=canonical_id,
                    platform_release_id=platform_row.id,
                    decision=decision,
                    score=score,
                    features_json=features_json,
                )
                self.session.add(row)
            else:
                row.decision = decision
                row.score = score
                row.features_json = features_json
            return row

        statement = select(LinkTrack).where(
            LinkTrack.track_id == canonical_id,
            LinkTrack.platform_track_id == platform_row.id,
        )
        row = self.session.scalar(statement)
        if row is None:
            row = LinkTrack(
                track_id=canonical_id,
                platform_track_id=platform_row.id,
                decision=decision,
                score=score,
                features_json=features_json,
            )
            self.session.add(row)
        else:
            row.decision = decision
            row.score = score
            row.features_json = features_json
        return row
