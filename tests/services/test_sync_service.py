from __future__ import annotations

from sqlalchemy import func, select

from app.core.config import Settings, get_settings
from app.db.models import PlatformArtist, SyncJob
from app.providers.base import ProviderArtist
from app.db.repositories.sync_jobs import SyncJobRepository
from app.providers import MusicProvider, ProviderEntityKind, ProviderName, ProviderRegistry
from app.services.artist_service import ArtistService
from app.services.link_service import LinkService
from app.services.release_service import ReleaseService
from app.services.sync_service import SyncService
from app.services.track_service import TrackService
from tests.test_support import StubProvider, make_artist, seed_catalog


class FlakyArtistProvider(MusicProvider):
    def __init__(self, *, provider_name: ProviderName, artist: ProviderArtist, fail_count: int) -> None:
        self.provider_name = provider_name
        self.artist = artist
        self.fail_count = fail_count
        self.calls = 0

    def search(self, query: str, *, limit: int, kind: ProviderEntityKind | None = None):
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


def build_sync_service(
    db_session,
    provider_registry: ProviderRegistry,
    settings: Settings | None = None,
) -> SyncService:
    return SyncService(
        session=db_session,
        settings=settings or get_settings(),
        provider_registry=provider_registry,
        link_service=LinkService(db_session),
        artist_service=ArtistService(db_session),
        release_service=ReleaseService(db_session),
        track_service=TrackService(db_session),
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
