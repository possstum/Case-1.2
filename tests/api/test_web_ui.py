from __future__ import annotations

from app.providers import ProviderEntityKind, ProviderName, ProviderRegistry, ProviderSearchHit
from tests.test_support import (
    AllowAllLimiter,
    DenyAllLimiter,
    RecordingSyncScheduler,
    StubProvider,
    create_test_client,
    make_artist,
    seed_catalog,
)


def test_root_redirects_to_ui_and_ui_landing_page_renders_without_providers() -> None:
    with create_test_client(limiter=AllowAllLimiter()) as client:
        redirect_response = client.get("/", follow_redirects=False)
        landing_response = client.get("/ui")

    assert redirect_response.status_code == 302
    assert redirect_response.headers["location"] == "/ui"

    assert landing_response.status_code == 200
    assert "Cross-platform matching without pretending certainty." in landing_response.text
    assert "Search is cache-first." in landing_response.text


def test_ui_search_renders_results_and_explainability(
    sqlite_database_url: str,
    migrated_sqlite_database,
) -> None:
    youtube_artist = make_artist(ProviderName.YOUTUBE, "yt-1", "Кровосток")
    yandex_artist = make_artist(ProviderName.YANDEX, "ya-1", "Krovostok")
    provider_registry = ProviderRegistry(
        (
            StubProvider(
                provider_name=ProviderName.YOUTUBE,
                search_hits=[ProviderSearchHit(kind=ProviderEntityKind.ARTIST, entity=youtube_artist)],
            ),
            StubProvider(
                provider_name=ProviderName.YANDEX,
                search_hits=[ProviderSearchHit(kind=ProviderEntityKind.ARTIST, entity=yandex_artist)],
            ),
        )
    )

    with create_test_client(provider_registry=provider_registry, limiter=AllowAllLimiter()) as client:
        response = client.get("/ui", params={"q": "Кровосток", "kind": "artist", "limit": 5})

    assert response.status_code == 200
    assert "Cross-platform matching without pretending certainty." in response.text
    assert "Open canonical entity" in response.text
    assert "features_json" in response.text


def test_ui_search_without_configured_providers_shows_notice(
    sqlite_database_url: str,
    migrated_sqlite_database,
) -> None:
    with create_test_client(limiter=AllowAllLimiter()) as client:
        response = client.get("/ui", params={"q": "Кровосток", "kind": "artist", "limit": 5})

    assert response.status_code == 200
    assert "Search providers are not configured." in response.text
    assert "The UI is available, but live search is disabled." in response.text


def test_ui_entity_and_job_pages_render(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    ids = seed_catalog(db_session)
    scheduler = RecordingSyncScheduler()

    with create_test_client(sync_scheduler=scheduler, limiter=AllowAllLimiter()) as client:
        artist_page = client.get(f"/ui/artists/{ids['artist_id']}")
        sync_response = client.post(
            f"/ui/sync/artist/{ids['artist_id']}",
            follow_redirects=False,
        )
        job_page = client.get(sync_response.headers["location"])

    assert artist_page.status_code == 200
    assert "Platform links" in artist_page.text
    assert "Enqueue sync" in artist_page.text

    assert sync_response.status_code == 303
    assert "/ui/jobs/" in sync_response.headers["location"]

    assert job_page.status_code == 200
    assert "Sync Job" in job_page.text
    assert "queued" in job_page.text


def test_ui_sync_rate_limit_returns_429(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    ids = seed_catalog(db_session)

    with create_test_client(limiter=DenyAllLimiter()) as client:
        response = client.post(
            f"/ui/sync/artist/{ids['artist_id']}",
            follow_redirects=False,
        )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limit_exceeded"
