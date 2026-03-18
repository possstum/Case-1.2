from __future__ import annotations

from sqlalchemy import func, select

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
from app.providers.yandex_music.schemas import (
    YandexMusicAlbumWithTracksPayload,
    YandexMusicArtistBriefInfoPayload,
    YandexMusicArtistDetailPayload,
    YandexMusicArtistDirectAlbumsPayload,
    YandexMusicArtistPayload,
    YandexMusicArtistTracksPayload,
    YandexMusicCollectionItemPayload,
    YandexMusicPagerPayload,
    YandexMusicReleasePayload,
    YandexMusicTrackPayload,
)
from app.services.link_service import LinkService
from app.services.yandex_catalog_service import YandexCatalogIngestionService


def _artist_payload(artist_id: str, name: str) -> YandexMusicArtistPayload:
    return YandexMusicArtistPayload(
        id=artist_id,
        name=name,
        aliases=[],
        url=f"https://music.yandex.ru/artist/{artist_id}",
        raw_json={"id": int(artist_id), "name": name},
    )


def _release_payload(
    release_id: str,
    title: str,
    *,
    artist_specs: list[tuple[str, str]],
    year: int | None = None,
    track_count: int | None = None,
    release_type: str | None = None,
) -> YandexMusicReleasePayload:
    return YandexMusicReleasePayload(
        id=release_id,
        title=title,
        artists=[name for _, name in artist_specs],
        release_type=release_type,
        year=year,
        track_count=track_count,
        url=f"https://music.yandex.ru/album/{release_id}",
        raw_json={
            "id": int(release_id),
            "title": title,
            "artists": [{"id": int(artist_id), "name": name} for artist_id, name in artist_specs],
            "year": year,
            "trackCount": track_count,
            "type": release_type,
        },
    )


def _track_payload(
    track_id: str,
    title: str,
    *,
    artist_specs: list[tuple[str, str]],
    album_id: str,
    album_title: str,
    track_number: int,
    disc_number: int = 1,
) -> YandexMusicTrackPayload:
    return YandexMusicTrackPayload(
        id=track_id,
        title=title,
        artists=[name for _, name in artist_specs],
        duration_ms=180000 + track_number,
        release_title=album_title,
        disc_number=disc_number,
        track_number=track_number,
        url=f"https://music.yandex.ru/track/{track_id}",
        raw_json={
            "id": int(track_id),
            "title": title,
            "durationMs": 180000 + track_number,
            "artists": [{"id": int(artist_id), "name": name} for artist_id, name in artist_specs],
            "albums": [
                {
                    "id": int(album_id),
                    "title": album_title,
                    "trackPosition": {"index": track_number, "volume": disc_number},
                }
            ],
        },
    )


class StubYandexCatalogProvider:
    def __init__(self) -> None:
        self.artist = _artist_payload("1014281", "Motorama")
        self.similar_artist = _artist_payload("202", "Human Tetris")
        self.feature_artist = _artist_payload("303", "Guest Singer")
        self.direct_release = _release_payload(
            "8460751",
            "Motorama EP",
            artist_specs=[("1014281", "Motorama")],
            year=2014,
            track_count=2,
        )
        self.archive_release = _release_payload(
            "8460752",
            "Archive Sessions",
            artist_specs=[("1014281", "Motorama")],
            year=2016,
            track_count=8,
            release_type="album",
        )
        self.compilation_release = _release_payload(
            "8460753",
            "Guest Compilation",
            artist_specs=[("1014281", "Motorama"), ("303", "Guest Singer")],
            year=2015,
            track_count=12,
        )
        self.popular_track = _track_payload(
            "119728832",
            "Motorama",
            artist_specs=[("1014281", "Motorama")],
            album_id="8460751",
            album_title="Motorama EP",
            track_number=1,
        )
        self.ghost_track = _track_payload(
            "119728833",
            "Ghost",
            artist_specs=[("1014281", "Motorama")],
            album_id="8460751",
            album_title="Motorama EP",
            track_number=2,
        )
        self.night_drive_track = _track_payload(
            "119728900",
            "Night Drive",
            artist_specs=[("1014281", "Motorama")],
            album_id="8460752",
            album_title="Archive Sessions",
            track_number=3,
        )
        self.release_with_track_calls: list[str] = []

    def get_artist_detail(self, provider_id: str) -> YandexMusicArtistDetailPayload:
        assert provider_id == self.artist.id
        return YandexMusicArtistDetailPayload(
            artist=self.artist,
            albums=[self.direct_release],
            also_albums=[self.compilation_release],
            popular_tracks=[self.popular_track],
            similar_artists=[self.similar_artist],
            last_releases=[self.archive_release],
            videos=[
                YandexMusicCollectionItemPayload(
                    id="video-1",
                    title="Live Session",
                    url="https://music.yandex.ru/video/video-1",
                    raw_json={"id": "video-1", "title": "Live Session"},
                )
            ],
            clips=[],
            vinyls=[],
            raw_json={},
        )

    def get_artist_brief_info(self, provider_id: str) -> YandexMusicArtistBriefInfoPayload:
        assert provider_id == self.artist.id
        return YandexMusicArtistBriefInfoPayload(
            artist=self.artist,
            albums=[self.direct_release],
            also_albums=[self.compilation_release],
            popular_tracks=[self.popular_track],
            similar_artists=[self.similar_artist],
            last_releases=[self.archive_release],
            videos=[],
            clips=[],
            vinyls=[],
            stats={"tracks": 42},
            playlist_ids=["pl-1"],
            playlists=[
                YandexMusicCollectionItemPayload(
                    id="pl-1",
                    title="Motorama Mix",
                    url="https://music.yandex.ru/users/demo/playlists/pl-1",
                    raw_json={"uid": "pl-1", "title": "Motorama Mix"},
                )
            ],
            links=[
                YandexMusicCollectionItemPayload(
                    id="wiki",
                    title="Wikipedia",
                    url="https://example.test/motorama",
                    raw_json={"title": "Wikipedia", "url": "https://example.test/motorama"},
                )
            ],
            has_trailer=True,
            raw_json={},
        )

    def get_artist_direct_albums(
        self,
        provider_id: str,
        *,
        page: int = 0,
        page_size: int = 20,
    ) -> YandexMusicArtistDirectAlbumsPayload:
        assert provider_id == self.artist.id
        assert page == 0
        assert page_size == 100
        return YandexMusicArtistDirectAlbumsPayload(
            artist_id=provider_id,
            pager=YandexMusicPagerPayload(page=0, per_page=1, total=1),
            albums=[self.direct_release],
            raw_json={"albums": [self.direct_release.raw_json]},
        )

    def get_artist_tracks(
        self,
        provider_id: str,
        *,
        page: int = 0,
        page_size: int = 20,
    ) -> YandexMusicArtistTracksPayload:
        assert provider_id == self.artist.id
        assert page == 0
        assert page_size == 100
        return YandexMusicArtistTracksPayload(
            artist_id=provider_id,
            pager=YandexMusicPagerPayload(page=0, per_page=2, total=2),
            tracks=[self.popular_track, self.night_drive_track],
            raw_json={"tracks": [self.popular_track.raw_json, self.night_drive_track.raw_json]},
        )

    def get_release_with_tracks(self, provider_id: str) -> YandexMusicAlbumWithTracksPayload:
        self.release_with_track_calls.append(provider_id)
        assert provider_id == self.direct_release.id
        return YandexMusicAlbumWithTracksPayload(
            release=self.direct_release,
            pager=YandexMusicPagerPayload(page=0, per_page=2, total=2),
            volumes=[[self.popular_track, self.ghost_track]],
            raw_json={"volumes": [[self.popular_track.raw_json, self.ghost_track.raw_json]]},
        )

    def get_track(self, provider_id: str):
        raise NotImplementedError


def test_yandex_catalog_ingestion_service_persists_artist_graph_idempotently(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    provider = StubYandexCatalogProvider()
    service = YandexCatalogIngestionService(
        session=db_session,
        provider=provider,
        link_service=LinkService(db_session),
    )

    summary_first = service.ingest_artist("1014281")
    db_session.commit()
    summary_second = service.ingest_artist("1014281")
    db_session.commit()
    db_session.expire_all()

    assert summary_first.artist_provider_id == "1014281"
    assert len(summary_first.platform_artist_ids) == 3
    assert len(summary_first.platform_release_ids) == 3
    assert len(summary_first.platform_track_ids) == 3
    assert len(summary_second.platform_artist_ids) == 3
    assert provider.release_with_track_calls == ["8460751", "8460751"]

    assert db_session.scalar(select(func.count()).select_from(PlatformArtist)) == 3
    assert db_session.scalar(select(func.count()).select_from(PlatformRelease)) == 3
    assert db_session.scalar(select(func.count()).select_from(PlatformTrack)) == 3
    assert db_session.scalar(select(func.count()).select_from(PlatformReleaseArtist)) == 4
    assert db_session.scalar(select(func.count()).select_from(PlatformTrackArtist)) == 3
    assert db_session.scalar(select(func.count()).select_from(PlatformReleaseTrack)) == 2

    direct_release = db_session.scalar(
        select(PlatformRelease).where(
            PlatformRelease.platform == "yandex",
            PlatformRelease.platform_id == "8460751",
        )
    )
    assert direct_release is not None
    assert direct_release.release_type == "ep"
    assert direct_release.release_type_source is None
    assert direct_release.release_type_confidence == "heuristic"

    archive_release = db_session.scalar(
        select(PlatformRelease).where(
            PlatformRelease.platform == "yandex",
            PlatformRelease.platform_id == "8460752",
        )
    )
    assert archive_release is not None
    assert archive_release.release_type == "album"
    assert archive_release.release_type_source == "album"
    assert archive_release.release_type_confidence == "exact"

    track_rows = db_session.scalars(
        select(PlatformReleaseTrack)
        .where(PlatformReleaseTrack.platform_release_id == direct_release.id)
        .order_by(PlatformReleaseTrack.position)
    ).all()
    assert [row.position for row in track_rows] == [1, 2]
    assert [row.track_number for row in track_rows] == [1, 2]
    assert [row.disc_number for row in track_rows] == [1, 1]

    direct_albums_list = db_session.scalar(
        select(PlatformCatalogList).where(
            PlatformCatalogList.platform == "yandex",
            PlatformCatalogList.owner_kind == "artist",
            PlatformCatalogList.owner_platform_id == "1014281",
            PlatformCatalogList.list_kind == "direct_albums",
            PlatformCatalogList.source_endpoint == "/artists/1014281/direct-albums",
        )
    )
    assert direct_albums_list is not None
    assert db_session.scalar(
        select(func.count()).select_from(PlatformCatalogListItem).where(
            PlatformCatalogListItem.catalog_list_id == direct_albums_list.id
        )
    ) == 1

    playlists_list = db_session.scalar(
        select(PlatformCatalogList).where(
            PlatformCatalogList.owner_platform_id == "1014281",
            PlatformCatalogList.list_kind == "playlists",
            PlatformCatalogList.source_endpoint == "/artists/1014281/brief-info",
        )
    )
    assert playlists_list is not None
    playlist_item = db_session.scalar(
        select(PlatformCatalogListItem).where(PlatformCatalogListItem.catalog_list_id == playlists_list.id)
    )
    assert playlist_item is not None
    assert playlist_item.item_kind == "playlist"
    assert playlist_item.external_ref == "pl-1"

    similar_artists_list = db_session.scalar(
        select(PlatformCatalogList).where(
            PlatformCatalogList.owner_platform_id == "1014281",
            PlatformCatalogList.list_kind == "similar_artists",
            PlatformCatalogList.source_endpoint == "/artists/1014281",
        )
    )
    assert similar_artists_list is not None
    similar_artist_item = db_session.scalar(
        select(PlatformCatalogListItem).where(
            PlatformCatalogListItem.catalog_list_id == similar_artists_list.id
        )
    )
    assert similar_artist_item is not None
    assert similar_artist_item.platform_artist_id is not None


def test_yandex_catalog_storage_supports_segmented_read_queries(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    provider = StubYandexCatalogProvider()
    service = YandexCatalogIngestionService(
        session=db_session,
        provider=provider,
        link_service=LinkService(db_session),
    )

    service.ingest_artist("1014281")
    db_session.commit()
    db_session.expire_all()

    artist_release_ids = db_session.scalars(
        select(PlatformRelease.platform_id)
        .join(
            PlatformReleaseArtist,
            PlatformReleaseArtist.platform_release_id == PlatformRelease.id,
        )
        .join(
            PlatformArtist,
            PlatformArtist.id == PlatformReleaseArtist.platform_artist_id,
        )
        .where(
            PlatformArtist.platform == "yandex",
            PlatformArtist.platform_id == "1014281",
        )
        .order_by(PlatformRelease.platform_id)
    ).all()
    assert artist_release_ids == ["8460751", "8460752", "8460753"]

    direct_album_ids = db_session.scalars(
        select(PlatformRelease.platform_id)
        .join(
            PlatformCatalogListItem,
            PlatformCatalogListItem.platform_release_id == PlatformRelease.id,
        )
        .join(
            PlatformCatalogList,
            PlatformCatalogList.id == PlatformCatalogListItem.catalog_list_id,
        )
        .where(
            PlatformCatalogList.platform == "yandex",
            PlatformCatalogList.owner_kind == "artist",
            PlatformCatalogList.owner_platform_id == "1014281",
            PlatformCatalogList.list_kind == "direct_albums",
            PlatformCatalogList.source_endpoint == "/artists/1014281/direct-albums",
        )
        .order_by(PlatformCatalogListItem.position)
    ).all()
    assert direct_album_ids == ["8460751"]

    artist_track_ids = db_session.scalars(
        select(PlatformTrack.platform_id)
        .join(
            PlatformCatalogListItem,
            PlatformCatalogListItem.platform_track_id == PlatformTrack.id,
        )
        .join(
            PlatformCatalogList,
            PlatformCatalogList.id == PlatformCatalogListItem.catalog_list_id,
        )
        .where(
            PlatformCatalogList.platform == "yandex",
            PlatformCatalogList.owner_kind == "artist",
            PlatformCatalogList.owner_platform_id == "1014281",
            PlatformCatalogList.list_kind == "artist_tracks",
            PlatformCatalogList.source_endpoint == "/artists/1014281/tracks",
        )
        .order_by(PlatformCatalogListItem.position)
    ).all()
    assert artist_track_ids == ["119728832", "119728900"]

    release_tracklist = db_session.execute(
        select(
            PlatformTrack.platform_id,
            PlatformReleaseTrack.disc_number,
            PlatformReleaseTrack.track_number,
        )
        .join(
            PlatformReleaseTrack,
            PlatformReleaseTrack.platform_track_id == PlatformTrack.id,
        )
        .join(
            PlatformRelease,
            PlatformRelease.id == PlatformReleaseTrack.platform_release_id,
        )
        .where(
            PlatformRelease.platform == "yandex",
            PlatformRelease.platform_id == "8460751",
        )
        .order_by(PlatformReleaseTrack.position)
    ).all()
    assert release_tracklist == [
        ("119728832", 1, 1),
        ("119728833", 1, 2),
    ]

    release_type_counts = db_session.execute(
        select(
            PlatformRelease.release_type,
            func.count(),
        )
        .where(PlatformRelease.platform == "yandex")
        .group_by(PlatformRelease.release_type)
        .order_by(PlatformRelease.release_type)
    ).all()
    assert release_type_counts == [
        ("album", 1),
        ("compilation", 1),
        ("ep", 1),
    ]
