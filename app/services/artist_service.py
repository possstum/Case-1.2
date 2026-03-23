from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas.entities import (
    ArtistAliasPayload,
    ArtistDetailResponse,
    ExplainabilityPayload,
    LinkedPlatformEntityPayload,
    MissingOnYandexCandidatePayload,
    MissingOnYandexItemPayload,
    MissingOnYandexViewPayload,
    ProviderCatalogSectionItemPayload,
    ProviderCatalogSectionPayload,
    RelatedReleasePayload,
    RelatedTrackPayload,
)
from app.core.errors import NotFoundError
from app.db.models import (
    Artist,
    LinkArtist,
    LinkRelease,
    PlatformCatalogList,
    PlatformCatalogListItem,
    PlatformRelease,
    Release,
    ReleaseArtist,
    TrackArtist,
)
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
                    track_count=len(credit.release.tracks),
                    role=credit.role,
                    position=credit.position,
                    available_platforms=self._release_available_platforms(credit.release.platform_links),
                    missing_platforms=self._release_missing_platforms(credit.release.platform_links),
                    is_missing_yandex=self._release_is_missing_yandex(credit.release.platform_links),
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
            yandex_catalog_sections=self._build_yandex_catalog_sections(artist),
            missing_on_yandex_view=self._build_missing_on_yandex_view(artist),
        )

    def get_artist_model(self, artist_id: int) -> Artist:
        statement = (
            select(Artist)
            .options(
                selectinload(Artist.aliases),
                selectinload(Artist.release_credits)
                .selectinload(ReleaseArtist.release)
                .selectinload(Release.tracks),
                selectinload(Artist.release_credits)
                .selectinload(ReleaseArtist.release)
                .selectinload(Release.platform_links)
                .selectinload(LinkRelease.platform_release),
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

    def _release_available_platforms(self, platform_links: list[LinkRelease]) -> list[str]:
        return sorted({link.platform_release.platform for link in platform_links})

    def _release_missing_platforms(self, platform_links: list[LinkRelease]) -> list[str]:
        available_platforms = set(self._release_available_platforms(platform_links))
        supported_platforms = {
            ProviderName.YOUTUBE.value,
            ProviderName.YANDEX.value,
        }
        return sorted(supported_platforms - available_platforms)

    def _release_is_missing_yandex(self, platform_links: list[LinkRelease]) -> bool:
        return ProviderName.YANDEX.value in self._release_missing_platforms(platform_links)

    def _build_yandex_catalog_sections(self, artist: Artist) -> list[ProviderCatalogSectionPayload]:
        rows = self._load_yandex_catalog_lists(
            artist,
            list_kinds=("direct_albums", "similar_artists"),
        )
        if not rows:
            return []

        section_order = {
            "direct_albums": 0,
            "similar_artists": 1,
        }
        grouped: dict[str, ProviderCatalogSectionPayload] = {}
        for row in rows:
            section = grouped.setdefault(
                row.list_kind,
                ProviderCatalogSectionPayload(
                    provider=ProviderName.YANDEX.value,
                    list_kind=row.list_kind,
                    title=self._catalog_section_title(row.list_kind),
                    total_items=row.total_items,
                    items=[],
                ),
            )
            if section.total_items is None and row.total_items is not None:
                section.total_items = row.total_items
            for item in sorted(row.items, key=lambda entry: entry.position):
                payload = self._catalog_section_item_payload(item)
                if payload is not None:
                    section.items.append(payload)

        return sorted(
            grouped.values(),
            key=lambda section: (section_order.get(section.list_kind, 9), section.title.casefold()),
        )

    def _catalog_section_item_payload(
        self,
        item: PlatformCatalogListItem,
    ) -> ProviderCatalogSectionItemPayload | None:
        if item.platform_release is not None:
            release = item.platform_release
            subtitle_parts = []
            if release.release_year is not None:
                subtitle_parts.append(str(release.release_year))
            if release.release_type:
                subtitle_parts.append(release.release_type)
            track_count = release.raw_json.get("track_count")
            if track_count is not None:
                track_label = "track" if track_count == 1 else "tracks"
                subtitle_parts.append(f"{track_count} {track_label}")
            return ProviderCatalogSectionItemPayload(
                item_kind="release",
                provider_id=release.platform_id,
                label=release.title,
                subtitle=" · ".join(subtitle_parts) if subtitle_parts else None,
                url=release.raw_json.get("url"),
            )

        if item.platform_artist is not None:
            platform_artist = item.platform_artist
            return ProviderCatalogSectionItemPayload(
                item_kind="artist",
                provider_id=platform_artist.platform_id,
                label=platform_artist.display_name,
                subtitle="Adjacent artist on Yandex",
                url=platform_artist.raw_json.get("url"),
            )

        title = item.raw_json.get("title") or item.external_ref
        if title is None:
            return None
        return ProviderCatalogSectionItemPayload(
            item_kind=item.item_kind,
            provider_id=item.external_ref,
            label=title,
            subtitle=None,
            url=item.raw_json.get("url"),
        )

    def _catalog_section_title(self, list_kind: str) -> str:
        titles = {
            "direct_albums": "Yandex direct albums",
            "similar_artists": "Adjacent artists on Yandex",
        }
        return titles.get(list_kind, list_kind.replace("_", " ").title())

    def _build_missing_on_yandex_view(self, artist: Artist) -> MissingOnYandexViewPayload:
        rows = [
            credit
            for credit in sorted(
                artist.release_credits,
                key=lambda item: (item.position, item.release.title.casefold()),
            )
            if self._release_is_missing_yandex(credit.release.platform_links)
        ]
        if not rows:
            return MissingOnYandexViewPayload()

        candidate_rows = self._load_yandex_catalog_lists(
            artist,
            list_kinds=("direct_albums", "albums", "also_albums", "last_releases"),
        )
        candidates = self._build_yandex_release_candidates(candidate_rows)

        items: list[MissingOnYandexItemPayload] = []
        for credit in rows:
            release = credit.release
            matching_candidates = self._match_yandex_candidates(release, candidates)
            status = "catalog_candidate" if matching_candidates else "missing"
            items.append(
                MissingOnYandexItemPayload(
                    release_id=release.id,
                    title=release.title,
                    release_type=release.release_type,
                    release_year=release.release_year,
                    track_count=len(release.tracks) if release.tracks else None,
                    role=credit.role,
                    position=credit.position,
                    status=status,
                    yandex_candidates=matching_candidates,
                )
            )

        candidate_count = sum(1 for item in items if item.status == "catalog_candidate")
        missing_count = sum(1 for item in items if item.status == "missing")
        return MissingOnYandexViewPayload(
            total_items=len(items),
            candidate_count=candidate_count,
            missing_count=missing_count,
            items=items,
        )

    def _load_yandex_catalog_lists(
        self,
        artist: Artist,
        *,
        list_kinds: tuple[str, ...],
    ) -> list[PlatformCatalogList]:
        yandex_link = next(
            (
                link
                for link in artist.platform_links
                if link.platform_artist.platform == ProviderName.YANDEX.value
            ),
            None,
        )
        if yandex_link is None:
            return []

        statement = (
            select(PlatformCatalogList)
            .options(
                selectinload(PlatformCatalogList.items).selectinload(PlatformCatalogListItem.platform_release),
                selectinload(PlatformCatalogList.items).selectinload(PlatformCatalogListItem.platform_artist),
            )
            .where(
                PlatformCatalogList.platform == ProviderName.YANDEX.value,
                PlatformCatalogList.owner_kind == "artist",
                PlatformCatalogList.owner_platform_id == yandex_link.platform_artist.platform_id,
                PlatformCatalogList.list_kind.in_(list_kinds),
            )
            .order_by(PlatformCatalogList.list_kind, PlatformCatalogList.page, PlatformCatalogList.id)
        )
        return self.session.scalars(statement).all()

    def _build_yandex_release_candidates(
        self,
        rows: list[PlatformCatalogList],
    ) -> list[tuple[PlatformRelease, list[str]]]:
        candidate_map: dict[str, tuple[PlatformRelease, set[str]]] = {}
        for row in rows:
            for item in sorted(row.items, key=lambda entry: entry.position):
                release = item.platform_release
                if release is None:
                    continue
                existing = candidate_map.get(release.platform_id)
                if existing is None:
                    candidate_map[release.platform_id] = (release, {row.list_kind})
                else:
                    existing[1].add(row.list_kind)
        return [
            (release, sorted(source_list_kinds))
            for release, source_list_kinds in candidate_map.values()
        ]

    def _match_yandex_candidates(
        self,
        release: Release,
        candidates: list[tuple[PlatformRelease, list[str]]],
    ) -> list[MissingOnYandexCandidatePayload]:
        matched: list[MissingOnYandexCandidatePayload] = []
        for candidate, source_list_kinds in candidates:
            if not self._is_yandex_catalog_candidate(release, candidate):
                continue
            matched.append(
                MissingOnYandexCandidatePayload(
                    provider_id=candidate.platform_id,
                    label=candidate.title,
                    release_type=candidate.release_type,
                    release_year=candidate.release_year,
                    source_list_kinds=source_list_kinds,
                    url=candidate.raw_json.get("url"),
                )
            )
        return sorted(
            matched,
            key=lambda item: (
                item.release_year or 0,
                item.label.casefold(),
                item.provider_id,
            ),
        )

    def _is_yandex_catalog_candidate(self, release: Release, candidate: PlatformRelease) -> bool:
        if release.match_norm != candidate.match_norm:
            return False
        if (
            release.release_year is not None
            and candidate.release_year is not None
            and release.release_year != candidate.release_year
        ):
            return False
        return True

    def _coerce_aware(self, value: datetime | None) -> datetime | None:
        if value is None or value.tzinfo is not None:
            return value
        return value.replace(tzinfo=timezone.utc)
