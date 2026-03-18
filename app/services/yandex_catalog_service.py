from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Protocol

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import (
    PlatformArtist,
    PlatformCatalogList,
    PlatformCatalogListItem,
    PlatformRelease,
    PlatformReleaseArtist,
    PlatformReleaseTrack,
    PlatformTrack,
    PlatformTrackArtist,
)
from app.db.models.mixins import utcnow
from app.providers.yandex_music.mapper import map_artist, map_release, map_track
from app.providers.yandex_music.schemas import (
    YandexMusicAlbumWithTracksPayload,
    YandexMusicArtistBriefInfoPayload,
    YandexMusicArtistDetailPayload,
    YandexMusicArtistDirectAlbumsPayload,
    YandexMusicArtistPayload,
    YandexMusicArtistTracksPayload,
    YandexMusicCollectionItemPayload,
    YandexMusicReleasePayload,
    YandexMusicTrackPayload,
)
from app.services.link_service import LinkService


RELEASE_TYPE_MARKERS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bep\b", re.IGNORECASE), "ep"),
    (re.compile(r"\blp\b", re.IGNORECASE), "lp"),
    (re.compile(r"\bsingle\b", re.IGNORECASE), "single"),
    (re.compile(r"\blive\b", re.IGNORECASE), "live"),
    (re.compile(r"\bremix\b", re.IGNORECASE), "remix"),
    (re.compile(r"\bsoundtrack\b|\bost\b", re.IGNORECASE), "soundtrack"),
    (re.compile(r"\bdemo\b", re.IGNORECASE), "demo"),
    (re.compile(r"\bmixtape\b", re.IGNORECASE), "mixtape"),
    (re.compile(r"\bcompilation\b|\bcompiled\b|\bbest of\b", re.IGNORECASE), "compilation"),
)
EXACT_RELEASE_TYPE_MAP = {
    "album": "album",
    "lp": "lp",
    "ep": "ep",
    "single": "single",
    "compilation": "compilation",
    "live": "live",
    "remix": "remix",
    "soundtrack": "soundtrack",
    "demo": "demo",
    "mixtape": "mixtape",
    "other": "other",
    "unknown": "unknown",
}


class YandexCatalogProvider(Protocol):
    def get_artist_detail(self, provider_id: str) -> YandexMusicArtistDetailPayload:
        ...

    def get_artist_brief_info(self, provider_id: str) -> YandexMusicArtistBriefInfoPayload:
        ...

    def get_artist_direct_albums(
        self,
        provider_id: str,
        *,
        page: int = 0,
        page_size: int = 20,
    ) -> YandexMusicArtistDirectAlbumsPayload:
        ...

    def get_artist_tracks(
        self,
        provider_id: str,
        *,
        page: int = 0,
        page_size: int = 20,
    ) -> YandexMusicArtistTracksPayload:
        ...

    def get_release_with_tracks(self, provider_id: str) -> YandexMusicAlbumWithTracksPayload:
        ...

    def get_track(self, provider_id: str):
        ...


@dataclass
class YandexCatalogIngestionSummary:
    artist_provider_id: str
    platform_artist_ids: set[int] = field(default_factory=set)
    platform_release_ids: set[int] = field(default_factory=set)
    platform_track_ids: set[int] = field(default_factory=set)
    catalog_list_ids: set[int] = field(default_factory=set)


class YandexCatalogIngestionService:
    def __init__(
        self,
        *,
        session: Session,
        provider: YandexCatalogProvider,
        link_service: LinkService,
        direct_albums_page_size: int = 100,
        artist_tracks_page_size: int = 100,
    ) -> None:
        self.session = session
        self.provider = provider
        self.link_service = link_service
        self.direct_albums_page_size = direct_albums_page_size
        self.artist_tracks_page_size = artist_tracks_page_size

    def ingest_artist(self, provider_id: str) -> YandexCatalogIngestionSummary:
        summary = YandexCatalogIngestionSummary(artist_provider_id=provider_id)

        detail = self.provider.get_artist_detail(provider_id)
        artist_row = self._persist_artist(detail.artist, summary)
        self._ingest_artist_detail_lists(
            artist_row=artist_row,
            payload=detail,
            source_endpoint=f"/artists/{provider_id}",
            summary=summary,
        )

        brief_info = self.provider.get_artist_brief_info(provider_id)
        artist_row = self._persist_artist(brief_info.artist, summary)
        self._ingest_artist_brief_lists(
            artist_row=artist_row,
            payload=brief_info,
            source_endpoint=f"/artists/{provider_id}/brief-info",
            summary=summary,
        )

        direct_albums = self.provider.get_artist_direct_albums(
            provider_id,
            page=0,
            page_size=self.direct_albums_page_size,
        )
        self._store_release_list(
            artist_row=artist_row,
            list_kind="direct_albums",
            source_endpoint=f"/artists/{provider_id}/direct-albums",
            releases=direct_albums.albums,
            raw_json=direct_albums.raw_json,
            page=direct_albums.pager.page if direct_albums.pager is not None and direct_albums.pager.page is not None else 0,
            page_size=direct_albums.pager.per_page if direct_albums.pager is not None else None,
            total_items=direct_albums.pager.total if direct_albums.pager is not None else None,
            summary=summary,
        )
        for release in direct_albums.albums:
            self.ingest_release(release.id, summary=summary)

        artist_tracks = self.provider.get_artist_tracks(
            provider_id,
            page=0,
            page_size=self.artist_tracks_page_size,
        )
        self._store_track_list(
            artist_row=artist_row,
            list_kind="artist_tracks",
            source_endpoint=f"/artists/{provider_id}/tracks",
            tracks=artist_tracks.tracks,
            raw_json=artist_tracks.raw_json,
            page=artist_tracks.pager.page if artist_tracks.pager is not None and artist_tracks.pager.page is not None else 0,
            page_size=artist_tracks.pager.per_page if artist_tracks.pager is not None else None,
            total_items=artist_tracks.pager.total if artist_tracks.pager is not None else None,
            summary=summary,
        )
        for track in artist_tracks.tracks:
            track_row = self._persist_track(track, summary)
            self._replace_track_artists(track_row, track.raw_json.get("artists"), summary)

        self.session.flush()
        return summary

    def ingest_release(
        self,
        provider_id: str,
        *,
        summary: Optional[YandexCatalogIngestionSummary] = None,
    ) -> PlatformRelease:
        payload = self.provider.get_release_with_tracks(provider_id)
        release_row = self._persist_release(payload.release, summary)
        self._replace_release_artists(release_row, payload.release.raw_json.get("artists"), summary)
        self._replace_release_tracklist(release_row, payload, summary)
        return release_row

    def ingest_track(
        self,
        provider_id: str,
        *,
        summary: Optional[YandexCatalogIngestionSummary] = None,
    ) -> PlatformTrack:
        track = self.provider.get_track(provider_id)
        track_row = self.link_service.persist_platform_entity(track)
        assert isinstance(track_row, PlatformTrack)
        if summary is not None:
            summary.platform_track_ids.add(track_row.id)
        self._replace_track_artists(track_row, track.raw_json.get("artists"), summary)
        return track_row

    def _ingest_artist_detail_lists(
        self,
        *,
        artist_row: PlatformArtist,
        payload: YandexMusicArtistDetailPayload,
        source_endpoint: str,
        summary: YandexCatalogIngestionSummary,
    ) -> None:
        self._store_release_list(
            artist_row=artist_row,
            list_kind="albums",
            source_endpoint=source_endpoint,
            releases=payload.albums,
            raw_json={"items": [release.raw_json for release in payload.albums]},
            page=0,
            page_size=len(payload.albums),
            total_items=len(payload.albums),
            summary=summary,
        )
        self._store_release_list(
            artist_row=artist_row,
            list_kind="also_albums",
            source_endpoint=source_endpoint,
            releases=payload.also_albums,
            raw_json={"items": [release.raw_json for release in payload.also_albums]},
            page=0,
            page_size=len(payload.also_albums),
            total_items=len(payload.also_albums),
            summary=summary,
        )
        self._store_track_list(
            artist_row=artist_row,
            list_kind="popular_tracks",
            source_endpoint=source_endpoint,
            tracks=payload.popular_tracks,
            raw_json={"items": [track.raw_json for track in payload.popular_tracks]},
            page=0,
            page_size=len(payload.popular_tracks),
            total_items=len(payload.popular_tracks),
            summary=summary,
        )
        self._store_artist_list(
            artist_row=artist_row,
            list_kind="similar_artists",
            source_endpoint=source_endpoint,
            artists=payload.similar_artists,
            raw_json={"items": [artist.raw_json for artist in payload.similar_artists]},
            page=0,
            page_size=len(payload.similar_artists),
            total_items=len(payload.similar_artists),
            summary=summary,
        )
        self._store_release_list(
            artist_row=artist_row,
            list_kind="last_releases",
            source_endpoint=source_endpoint,
            releases=payload.last_releases,
            raw_json={"items": [release.raw_json for release in payload.last_releases]},
            page=0,
            page_size=len(payload.last_releases),
            total_items=len(payload.last_releases),
            summary=summary,
        )
        self._store_collection_list(
            artist_row=artist_row,
            list_kind="videos",
            source_endpoint=source_endpoint,
            item_kind="video",
            items=payload.videos,
            raw_json={"items": [item.raw_json for item in payload.videos]},
            summary=summary,
        )
        self._store_collection_list(
            artist_row=artist_row,
            list_kind="clips",
            source_endpoint=source_endpoint,
            item_kind="video",
            items=payload.clips,
            raw_json={"items": [item.raw_json for item in payload.clips]},
            summary=summary,
        )
        self._store_collection_list(
            artist_row=artist_row,
            list_kind="vinyls",
            source_endpoint=source_endpoint,
            item_kind="unknown",
            items=payload.vinyls,
            raw_json={"items": [item.raw_json for item in payload.vinyls]},
            summary=summary,
        )

    def _ingest_artist_brief_lists(
        self,
        *,
        artist_row: PlatformArtist,
        payload: YandexMusicArtistBriefInfoPayload,
        source_endpoint: str,
        summary: YandexCatalogIngestionSummary,
    ) -> None:
        self._ingest_artist_detail_lists(
            artist_row=artist_row,
            payload=payload,
            source_endpoint=source_endpoint,
            summary=summary,
        )
        self._store_collection_list(
            artist_row=artist_row,
            list_kind="playlists",
            source_endpoint=source_endpoint,
            item_kind="playlist",
            items=payload.playlists,
            raw_json={
                "items": [item.raw_json for item in payload.playlists],
                "playlist_ids": payload.playlist_ids,
                "stats": payload.stats,
                "has_trailer": payload.has_trailer,
            },
            summary=summary,
        )
        self._store_collection_list(
            artist_row=artist_row,
            list_kind="links",
            source_endpoint=source_endpoint,
            item_kind="unknown",
            items=payload.links,
            raw_json={"items": [item.raw_json for item in payload.links]},
            summary=summary,
        )

    def _persist_artist(
        self,
        payload: YandexMusicArtistPayload,
        summary: Optional[YandexCatalogIngestionSummary],
    ) -> PlatformArtist:
        row = self.link_service.persist_platform_entity(map_artist(payload))
        assert isinstance(row, PlatformArtist)
        if summary is not None:
            summary.platform_artist_ids.add(row.id)
        return row

    def _persist_release(
        self,
        payload: YandexMusicReleasePayload,
        summary: Optional[YandexCatalogIngestionSummary],
    ) -> PlatformRelease:
        row = self.link_service.persist_platform_entity(map_release(payload))
        assert isinstance(row, PlatformRelease)
        normalized, confidence = self._classify_release(payload)
        row.release_type = normalized
        row.release_type_source = payload.release_type
        row.release_type_confidence = confidence
        row.release_year = payload.year
        row.raw_json = payload.raw_json
        row.fetched_at = utcnow()
        self.session.flush()
        if summary is not None:
            summary.platform_release_ids.add(row.id)
        return row

    def _persist_track(
        self,
        payload: YandexMusicTrackPayload,
        summary: Optional[YandexCatalogIngestionSummary],
    ) -> PlatformTrack:
        row = self.link_service.persist_platform_entity(map_track(payload))
        assert isinstance(row, PlatformTrack)
        if summary is not None:
            summary.platform_track_ids.add(row.id)
        return row

    def _replace_release_artists(
        self,
        release_row: PlatformRelease,
        artists_payload: object,
        summary: Optional[YandexCatalogIngestionSummary],
    ) -> None:
        self.session.execute(
            delete(PlatformReleaseArtist).where(PlatformReleaseArtist.platform_release_id == release_row.id)
        )
        self.session.flush()

        for position, artist_payload in enumerate(self._artist_payloads_from_raw(artists_payload)):
            artist_row = self._persist_artist(artist_payload, summary)
            self.session.add(
                PlatformReleaseArtist(
                    platform_release_id=release_row.id,
                    platform_artist_id=artist_row.id,
                    role="primary",
                    position=position,
                    raw_json=artist_payload.raw_json,
                )
            )
        self.session.flush()

    def _replace_track_artists(
        self,
        track_row: PlatformTrack,
        artists_payload: object,
        summary: Optional[YandexCatalogIngestionSummary],
    ) -> None:
        self.session.execute(
            delete(PlatformTrackArtist).where(PlatformTrackArtist.platform_track_id == track_row.id)
        )
        self.session.flush()

        for position, artist_payload in enumerate(self._artist_payloads_from_raw(artists_payload)):
            artist_row = self._persist_artist(artist_payload, summary)
            self.session.add(
                PlatformTrackArtist(
                    platform_track_id=track_row.id,
                    platform_artist_id=artist_row.id,
                    role="primary",
                    position=position,
                    raw_json=artist_payload.raw_json,
                )
            )
        self.session.flush()

    def _replace_release_tracklist(
        self,
        release_row: PlatformRelease,
        payload: YandexMusicAlbumWithTracksPayload,
        summary: Optional[YandexCatalogIngestionSummary],
    ) -> None:
        self.session.execute(
            delete(PlatformReleaseTrack).where(PlatformReleaseTrack.platform_release_id == release_row.id)
        )
        self.session.flush()

        position = 1
        for fallback_disc_number, volume in enumerate(payload.volumes, start=1):
            for fallback_track_number, track_payload in enumerate(volume, start=1):
                track_row = self._persist_track(track_payload, summary)
                self._replace_track_artists(track_row, track_payload.raw_json.get("artists"), summary)
                self.session.add(
                    PlatformReleaseTrack(
                        platform_release_id=release_row.id,
                        platform_track_id=track_row.id,
                        disc_number=track_payload.disc_number or fallback_disc_number,
                        track_number=track_payload.track_number or fallback_track_number,
                        position=position,
                        raw_json=track_payload.raw_json,
                    )
                )
                position += 1
        self.session.flush()

    def _store_artist_list(
        self,
        *,
        artist_row: PlatformArtist,
        list_kind: str,
        source_endpoint: str,
        artists: list[YandexMusicArtistPayload],
        raw_json: dict[str, object],
        page: int,
        page_size: Optional[int],
        total_items: Optional[int],
        summary: YandexCatalogIngestionSummary,
    ) -> None:
        list_row = self._upsert_catalog_list(
            artist_row=artist_row,
            list_kind=list_kind,
            source_endpoint=source_endpoint,
            raw_json=raw_json,
            page=page,
            page_size=page_size,
            total_items=total_items,
            summary=summary,
        )
        items: list[PlatformCatalogListItem] = []
        for position, payload in enumerate(artists):
            platform_artist = self._persist_artist(payload, summary)
            items.append(
                PlatformCatalogListItem(
                    catalog_list_id=list_row.id,
                    position=position,
                    item_kind="artist",
                    platform_artist_id=platform_artist.id,
                    external_ref=platform_artist.platform_id,
                    raw_json=payload.raw_json,
                )
            )
        self._replace_catalog_list_items(list_row, items)

    def _store_release_list(
        self,
        *,
        artist_row: PlatformArtist,
        list_kind: str,
        source_endpoint: str,
        releases: list[YandexMusicReleasePayload],
        raw_json: dict[str, object],
        page: int,
        page_size: Optional[int],
        total_items: Optional[int],
        summary: YandexCatalogIngestionSummary,
    ) -> None:
        list_row = self._upsert_catalog_list(
            artist_row=artist_row,
            list_kind=list_kind,
            source_endpoint=source_endpoint,
            raw_json=raw_json,
            page=page,
            page_size=page_size,
            total_items=total_items,
            summary=summary,
        )
        items: list[PlatformCatalogListItem] = []
        for position, payload in enumerate(releases):
            release_row = self._persist_release(payload, summary)
            self._replace_release_artists(release_row, payload.raw_json.get("artists"), summary)
            items.append(
                PlatformCatalogListItem(
                    catalog_list_id=list_row.id,
                    position=position,
                    item_kind="release",
                    platform_release_id=release_row.id,
                    external_ref=release_row.platform_id,
                    raw_json=payload.raw_json,
                )
            )
        self._replace_catalog_list_items(list_row, items)

    def _store_track_list(
        self,
        *,
        artist_row: PlatformArtist,
        list_kind: str,
        source_endpoint: str,
        tracks: list[YandexMusicTrackPayload],
        raw_json: dict[str, object],
        page: int,
        page_size: Optional[int],
        total_items: Optional[int],
        summary: YandexCatalogIngestionSummary,
    ) -> None:
        list_row = self._upsert_catalog_list(
            artist_row=artist_row,
            list_kind=list_kind,
            source_endpoint=source_endpoint,
            raw_json=raw_json,
            page=page,
            page_size=page_size,
            total_items=total_items,
            summary=summary,
        )
        items: list[PlatformCatalogListItem] = []
        for position, payload in enumerate(tracks):
            track_row = self._persist_track(payload, summary)
            self._replace_track_artists(track_row, payload.raw_json.get("artists"), summary)
            items.append(
                PlatformCatalogListItem(
                    catalog_list_id=list_row.id,
                    position=position,
                    item_kind="track",
                    platform_track_id=track_row.id,
                    external_ref=track_row.platform_id,
                    raw_json=payload.raw_json,
                )
            )
        self._replace_catalog_list_items(list_row, items)

    def _store_collection_list(
        self,
        *,
        artist_row: PlatformArtist,
        list_kind: str,
        source_endpoint: str,
        item_kind: str,
        items: list[YandexMusicCollectionItemPayload],
        raw_json: dict[str, object],
        summary: YandexCatalogIngestionSummary,
    ) -> None:
        list_row = self._upsert_catalog_list(
            artist_row=artist_row,
            list_kind=list_kind,
            source_endpoint=source_endpoint,
            raw_json=raw_json,
            page=0,
            page_size=len(items),
            total_items=len(items),
            summary=summary,
        )
        list_items = [
            PlatformCatalogListItem(
                catalog_list_id=list_row.id,
                position=position,
                item_kind=item_kind,
                external_ref=self._collection_external_ref(item),
                raw_json=item.raw_json,
            )
            for position, item in enumerate(items)
        ]
        self._replace_catalog_list_items(list_row, list_items)

    def _upsert_catalog_list(
        self,
        *,
        artist_row: PlatformArtist,
        list_kind: str,
        source_endpoint: str,
        raw_json: dict[str, object],
        page: int,
        page_size: Optional[int],
        total_items: Optional[int],
        summary: YandexCatalogIngestionSummary,
    ) -> PlatformCatalogList:
        statement = select(PlatformCatalogList).where(
            PlatformCatalogList.platform == artist_row.platform,
            PlatformCatalogList.owner_kind == "artist",
            PlatformCatalogList.owner_platform_id == artist_row.platform_id,
            PlatformCatalogList.list_kind == list_kind,
            PlatformCatalogList.source_endpoint == source_endpoint,
            PlatformCatalogList.page == page,
        )
        row = self.session.scalar(statement)
        if row is None:
            row = PlatformCatalogList(
                platform=artist_row.platform,
                owner_kind="artist",
                owner_platform_id=artist_row.platform_id,
                list_kind=list_kind,
                source_endpoint=source_endpoint,
                title=f"{artist_row.display_name} {list_kind}",
                page=page,
                page_size=page_size,
                total_items=total_items,
                raw_json=raw_json,
            )
            self.session.add(row)
            self.session.flush()
        else:
            row.title = f"{artist_row.display_name} {list_kind}"
            row.page_size = page_size
            row.total_items = total_items
            row.raw_json = raw_json
            row.fetched_at = utcnow()
            self.session.flush()
        summary.catalog_list_ids.add(row.id)
        return row

    def _replace_catalog_list_items(
        self,
        list_row: PlatformCatalogList,
        items: list[PlatformCatalogListItem],
    ) -> None:
        self.session.execute(
            delete(PlatformCatalogListItem).where(PlatformCatalogListItem.catalog_list_id == list_row.id)
        )
        self.session.flush()
        for item in items:
            self.session.add(item)
        self.session.flush()

    def _artist_payloads_from_raw(self, payload: object) -> list[YandexMusicArtistPayload]:
        if not isinstance(payload, list):
            return []
        artists: list[YandexMusicArtistPayload] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            provider_id = item.get("id")
            name = item.get("name")
            if not isinstance(provider_id, (int, str)) or not isinstance(name, str) or not name:
                continue
            artists.append(
                YandexMusicArtistPayload(
                    id=str(provider_id),
                    name=name,
                    aliases=[],
                    url=f"https://music.yandex.ru/artist/{provider_id}",
                    raw_json=item,
                )
            )
        return artists

    def _classify_release(self, payload: YandexMusicReleasePayload) -> tuple[str, str]:
        release_type_source = (payload.release_type or "").strip().lower()
        if release_type_source in EXACT_RELEASE_TYPE_MAP:
            return EXACT_RELEASE_TYPE_MAP[release_type_source], "exact"

        title = payload.title.strip()
        for pattern, normalized in RELEASE_TYPE_MARKERS:
            if pattern.search(title):
                return normalized, "heuristic"
        return "unknown", "ambiguous"

    def _collection_external_ref(self, item: YandexMusicCollectionItemPayload) -> Optional[str]:
        return item.id or item.url or item.title or item.name
