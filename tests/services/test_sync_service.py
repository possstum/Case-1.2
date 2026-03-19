from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select

from app.core.config import Settings, get_settings
from app.db.models import LinkRelease, PlatformArtist, PlatformRelease, SyncJob
from app.providers.base import ProviderArtist
from app.db.repositories.sync_jobs import SyncJobRepository
from app.providers import MusicProvider, ProviderEntityKind, ProviderName, ProviderRegistry
from app.services.artist_service import ArtistService
from app.services.link_service import LinkService
from app.services.release_service import ReleaseService
from app.services.sync_service import SyncService
from app.services.track_service import TrackService
from app.services.yandex_catalog_service import YandexCatalogIngestionSummary
from app.utils.normalization import display_norm, match_norm
from tests.test_support import StubProvider, make_artist, make_release, make_track, seed_catalog


class FlakyArtistProvider(MusicProvider):
    def __init__(self, *, provider_name: ProviderName, artist: ProviderArtist, fail_count: int) -> None:
        self.provider_name = provider_name
        self.artist = artist
        self.fail_count = fail_count
        self.calls = 0

    def search(self, query: str, *, limit: int | None, kind: ProviderEntityKind | None = None):
        raise NotImplementedError

    def get_artist(self, provider_id: str) -> ProviderArtist:
        self.calls += 1
        if self.calls <= self.fail_count:
            raise RuntimeError("temporary provider failure")
        return self.artist

    def get_release(self, provider_id: str):
        raise NotImplementedError

    def get_track(self, provider_id: str):
        raise NotImplementedError


@dataclass
class StubCatalogEntity:
    id: int
    platform_id: str


class RecordingYandexCatalogIngestionService:
    def __init__(self) -> None:
        self.artist_calls: list[str] = []
        self.release_calls: list[str] = []
        self.track_calls: list[str] = []

    def ingest_artist(self, provider_id: str) -> YandexCatalogIngestionSummary:
        self.artist_calls.append(provider_id)
        return YandexCatalogIngestionSummary(
            artist_provider_id=provider_id,
            platform_artist_ids={101, 102},
            platform_release_ids={201, 202, 203},
            platform_track_ids={301, 302},
            catalog_list_ids={401, 402, 403, 404},
        )

    def ingest_release(self, provider_id: str) -> StubCatalogEntity:
        self.release_calls.append(provider_id)
        return StubCatalogEntity(id=501, platform_id=provider_id)

    def ingest_track(self, provider_id: str) -> StubCatalogEntity:
        self.track_calls.append(provider_id)
        return StubCatalogEntity(id=601, platform_id=provider_id)


def build_sync_service(
    db_session,
    provider_registry: ProviderRegistry,
    settings: Settings | None = None,
    yandex_catalog_ingestion_service: RecordingYandexCatalogIngestionService | None = None,
) -> SyncService:
    return SyncService(
        session=db_session,
        settings=settings or get_settings(),
        provider_registry=provider_registry,
        link_service=LinkService(db_session),
        artist_service=ArtistService(db_session),
        release_service=ReleaseService(db_session),
        track_service=TrackService(db_session),
        yandex_catalog_ingestion_service=yandex_catalog_ingestion_service,
    )


def test_sync_service_refreshes_platform_rows_without_duplicates(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    ids = seed_catalog(db_session)
    repository = SyncJobRepository(db_session)
    sync_job = repository.create(
        kind="artist",
        target_id=str(ids["artist_id"]),
        queue_name="default",
        payload_json={"kind": "artist", "target_id": str(ids["artist_id"])},
    )
    db_session.commit()

    youtube_artist = make_artist(
        ProviderName.YOUTUBE,
        "yt-artist-1",
        "Кровосток",
        url="https://sync.youtube.test/artist/yt-artist-1",
    )
    yandex_artist = make_artist(
        ProviderName.YANDEX,
        "ya-artist-1",
        "Krovostok",
        url="https://sync.yandex.test/artist/ya-artist-1",
    )
    service = build_sync_service(
        db_session,
        ProviderRegistry(
            (
                StubProvider(provider_name=ProviderName.YOUTUBE, artists={"yt-artist-1": youtube_artist}),
                StubProvider(provider_name=ProviderName.YANDEX, artists={"ya-artist-1": yandex_artist}),
            )
        ),
    )

    response = service.execute(sync_job.id)

    assert response.status == "finished"
    assert response.result_json["updated_count"] == 2

    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(PlatformArtist)) == 2
    refreshed = db_session.scalar(
        select(PlatformArtist).where(
            PlatformArtist.platform == "youtube",
            PlatformArtist.platform_id == "yt-artist-1",
        )
    )
    assert refreshed is not None
    assert refreshed.raw_json["url"] == "https://sync.youtube.test/artist/yt-artist-1"


def test_sync_service_marks_failed_when_all_providers_fail(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    ids = seed_catalog(db_session)
    repository = SyncJobRepository(db_session)
    sync_job = repository.create(
        kind="artist",
        target_id=str(ids["artist_id"]),
        queue_name="default",
        payload_json={"kind": "artist", "target_id": str(ids["artist_id"])},
    )
    db_session.commit()

    failing_registry = ProviderRegistry(
        (
            StubProvider(provider_name=ProviderName.YOUTUBE, get_error=RuntimeError("provider down")),
            StubProvider(provider_name=ProviderName.YANDEX, get_error=RuntimeError("provider down")),
        )
    )
    service = build_sync_service(db_session, failing_registry)

    response = service.execute(sync_job.id)

    assert response.status == "failed"
    assert response.error_json["reason"] == "provider_refresh_failed"

    db_session.expire_all()
    stored_job = db_session.get(SyncJob, sync_job.id)
    assert stored_job is not None
    assert stored_job.status == "failed"


def test_sync_service_finishes_partial_when_youtube_fails_and_yandex_catalog_ingest_succeeds(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    ids = seed_catalog(db_session)
    repository = SyncJobRepository(db_session)
    sync_job = repository.create(
        kind="artist",
        target_id=str(ids["artist_id"]),
        queue_name="default",
        payload_json={"kind": "artist", "target_id": str(ids["artist_id"])},
    )
    db_session.commit()

    yandex_ingestion = RecordingYandexCatalogIngestionService()
    service = build_sync_service(
        db_session,
        ProviderRegistry(
            (
                StubProvider(
                    provider_name=ProviderName.YOUTUBE,
                    get_error=NotImplementedError("YouTube Music provider integration is not implemented yet"),
                ),
                StubProvider(
                    provider_name=ProviderName.YANDEX,
                    get_error=AssertionError("yandex provider get_* should not be called during catalog ingest"),
                ),
            )
        ),
        yandex_catalog_ingestion_service=yandex_ingestion,
    )

    response = service.execute(sync_job.id)

    assert response.status == "finished"
    assert response.result_json["updated_count"] == 1
    assert response.result_json["partial"] is True
    assert yandex_ingestion.artist_calls == ["ya-artist-1"]

    provider_results = {
        provider_result["provider"]: provider_result
        for provider_result in response.result_json["providers"]
    }
    assert provider_results["youtube"]["status"] == "failed"
    assert provider_results["yandex"]["status"] == "updated"
    assert provider_results["yandex"]["mode"] == "catalog_ingest"
    assert provider_results["yandex"]["catalog_list_count"] == 4


def test_sync_service_applies_retry_backoff_between_attempts(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
    monkeypatch,
) -> None:
    ids = seed_catalog(db_session)
    repository = SyncJobRepository(db_session)
    sync_job = repository.create(
        kind="artist",
        target_id=str(ids["artist_id"]),
        queue_name="default",
        payload_json={"kind": "artist", "target_id": str(ids["artist_id"])},
    )
    db_session.commit()

    youtube_artist = make_artist(
        ProviderName.YOUTUBE,
        "yt-artist-1",
        "Кровосток",
        url="https://sync.youtube.test/artist/yt-artist-1",
    )
    yandex_artist = make_artist(
        ProviderName.YANDEX,
        "ya-artist-1",
        "Krovostok",
        url="https://sync.yandex.test/artist/ya-artist-1",
    )
    flaky_provider = FlakyArtistProvider(
        provider_name=ProviderName.YOUTUBE,
        artist=youtube_artist,
        fail_count=1,
    )
    sleep_calls: list[float] = []
    monkeypatch.setattr("app.services.sync_service.time.sleep", lambda seconds: sleep_calls.append(seconds))

    service = build_sync_service(
        db_session,
        ProviderRegistry(
            (
                flaky_provider,
                StubProvider(provider_name=ProviderName.YANDEX, artists={"ya-artist-1": yandex_artist}),
            )
        ),
        settings=get_settings().model_copy(
            update={
                "sync_provider_max_attempts": 2,
                "sync_provider_retry_backoff_seconds": 0.25,
            }
        ),
    )

    response = service.execute(sync_job.id)

    assert response.status == "finished"
    assert response.result_json["updated_count"] == 2
    assert any(
        provider_result["provider"] == "youtube" and provider_result["attempts"] == 2
        for provider_result in response.result_json["providers"]
    )
    assert sleep_calls == [0.25]


def test_sync_service_uses_yandex_catalog_ingestion_for_artist_links(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    ids = seed_catalog(db_session)
    repository = SyncJobRepository(db_session)
    sync_job = repository.create(
        kind="artist",
        target_id=str(ids["artist_id"]),
        queue_name="default",
        payload_json={"kind": "artist", "target_id": str(ids["artist_id"])},
    )
    db_session.commit()

    youtube_artist = make_artist(
        ProviderName.YOUTUBE,
        "yt-artist-1",
        "Кровосток",
        url="https://sync.youtube.test/artist/yt-artist-1",
    )
    yandex_ingestion = RecordingYandexCatalogIngestionService()
    service = build_sync_service(
        db_session,
        ProviderRegistry(
            (
                StubProvider(provider_name=ProviderName.YOUTUBE, artists={"yt-artist-1": youtube_artist}),
                StubProvider(
                    provider_name=ProviderName.YANDEX,
                    get_error=AssertionError("yandex provider get_* should not be called during catalog ingest"),
                ),
            )
        ),
        yandex_catalog_ingestion_service=yandex_ingestion,
    )

    response = service.execute(sync_job.id)

    assert response.status == "finished"
    assert response.result_json["updated_count"] == 2
    assert response.result_json["partial"] is False
    assert yandex_ingestion.artist_calls == ["ya-artist-1"]

    provider_results = {
        provider_result["provider"]: provider_result
        for provider_result in response.result_json["providers"]
    }
    assert provider_results["youtube"]["status"] == "updated"
    assert provider_results["youtube"]["mode"] == "entity_refresh"
    assert provider_results["yandex"]["status"] == "updated"
    assert provider_results["yandex"]["mode"] == "catalog_ingest"
    assert provider_results["yandex"]["catalog_artist_provider_id"] == "ya-artist-1"
    assert provider_results["yandex"]["platform_artist_count"] == 2
    assert provider_results["yandex"]["platform_release_count"] == 3
    assert provider_results["yandex"]["platform_track_count"] == 2
    assert provider_results["yandex"]["catalog_list_count"] == 4


def test_sync_service_uses_yandex_catalog_ingestion_for_release_links(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    ids = seed_catalog(db_session)
    yandex_release = PlatformRelease(
        platform="yandex",
        platform_id="ya-release-1",
        title="Studio Session",
        display_norm=display_norm("Studio Session"),
        match_norm=match_norm("Studio Session"),
        release_type="album",
        release_year=2024,
        raw_json={
            "artist_names": ["Krovostok"],
            "track_count": 1,
            "url": "https://sync.yandex.test/release/ya-release-1",
        },
    )
    db_session.add(yandex_release)
    db_session.flush()
    db_session.add(
        LinkRelease(
            release_id=ids["release_id"],
            platform_release_id=yandex_release.id,
            decision="auto",
            score=0.95,
            features_json={"title_similarity": 0.98, "year_delta": 0},
        )
    )
    repository = SyncJobRepository(db_session)
    sync_job = repository.create(
        kind="release",
        target_id=str(ids["release_id"]),
        queue_name="default",
        payload_json={"kind": "release", "target_id": str(ids["release_id"])},
    )
    db_session.commit()

    youtube_release = make_release(
        ProviderName.YOUTUBE,
        "yt-release-1",
        "Studio Session",
        artist_names=["Krovostok"],
        release_year=2024,
        url="https://sync.youtube.test/release/yt-release-1",
    )
    yandex_ingestion = RecordingYandexCatalogIngestionService()
    service = build_sync_service(
        db_session,
        ProviderRegistry(
            (
                StubProvider(provider_name=ProviderName.YOUTUBE, releases={"yt-release-1": youtube_release}),
                StubProvider(
                    provider_name=ProviderName.YANDEX,
                    get_error=AssertionError("yandex provider get_* should not be called during catalog ingest"),
                ),
            )
        ),
        yandex_catalog_ingestion_service=yandex_ingestion,
    )

    response = service.execute(sync_job.id)

    assert response.status == "finished"
    assert response.result_json["updated_count"] == 2
    assert yandex_ingestion.release_calls == ["ya-release-1"]

    provider_results = {
        provider_result["provider"]: provider_result
        for provider_result in response.result_json["providers"]
    }
    assert provider_results["youtube"]["mode"] == "entity_refresh"
    assert provider_results["yandex"]["mode"] == "catalog_ingest"
    assert provider_results["yandex"]["platform_release_id"] == 501
    assert provider_results["yandex"]["platform_release_provider_id"] == "ya-release-1"


def test_sync_service_uses_yandex_catalog_ingestion_for_track_links(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    ids = seed_catalog(db_session)
    repository = SyncJobRepository(db_session)
    sync_job = repository.create(
        kind="track",
        target_id=str(ids["track_id"]),
        queue_name="default",
        payload_json={"kind": "track", "target_id": str(ids["track_id"])},
    )
    db_session.commit()

    youtube_track = make_track(
        ProviderName.YOUTUBE,
        "yt-track-1",
        "Biography",
        artist_names=["Krovostok"],
        duration_ms=185000,
        url="https://sync.youtube.test/track/yt-track-1",
    )
    yandex_ingestion = RecordingYandexCatalogIngestionService()
    service = build_sync_service(
        db_session,
        ProviderRegistry(
            (
                StubProvider(provider_name=ProviderName.YOUTUBE, tracks={"yt-track-1": youtube_track}),
                StubProvider(
                    provider_name=ProviderName.YANDEX,
                    get_error=AssertionError("yandex provider get_* should not be called during catalog ingest"),
                ),
            )
        ),
        yandex_catalog_ingestion_service=yandex_ingestion,
    )

    response = service.execute(sync_job.id)

    assert response.status == "finished"
    assert response.result_json["updated_count"] == 2
    assert yandex_ingestion.track_calls == ["ya-track-1"]

    provider_results = {
        provider_result["provider"]: provider_result
        for provider_result in response.result_json["providers"]
    }
    assert provider_results["youtube"]["mode"] == "entity_refresh"
    assert provider_results["yandex"]["mode"] == "catalog_ingest"
    assert provider_results["yandex"]["platform_track_id"] == 601
    assert provider_results["yandex"]["platform_track_provider_id"] == "ya-track-1"
