from __future__ import annotations

from unittest.mock import Mock, call

import pytest

from app.api.deps import get_web_search_service
from app.api.schemas.search import SearchCacheMetadata, SearchResponse
from app.providers import ProviderEntityKind, ProviderName, ProviderRegistry, ProviderSearchHit
from tests.test_support import (
    AllowAllLimiter,
    DenyAllLimiter,
    RecordingSyncScheduler,
    StubProvider,
    create_test_client,
    make_artist,
    make_release,
    make_track,
    seed_catalog,
)


def test_root_redirects_to_ui_and_ui_landing_page_renders_without_providers() -> None:
    with create_test_client(limiter=AllowAllLimiter()) as client:
        redirect_response = client.get("/", follow_redirects=False)
        landing_response = client.get("/ui")

    assert redirect_response.status_code == 302
    assert redirect_response.headers["location"] == "/ui"

    assert landing_response.status_code == 200
    assert "data-ui-search-form='true'" in landing_response.text
    assert "Cross-platform matching without pretending certainty." in landing_response.text
    assert "Search is cache-first." in landing_response.text


@pytest.mark.parametrize(
    ("kind", "provider_search_hit"),
    [
        (
            "artist",
            ProviderSearchHit(
                kind=ProviderEntityKind.ARTIST,
                entity=make_artist(ProviderName.YOUTUBE, "yt-artist-1", "Кровосток"),
            ),
        ),
        (
            "release",
            ProviderSearchHit(
                kind=ProviderEntityKind.RELEASE,
                entity=make_release(
                    ProviderName.YOUTUBE,
                    "yt-release-1",
                    "Studio Session",
                    artist_names=["Кровосток"],
                    release_year=2024,
                ),
            ),
        ),
        (
            "track",
            ProviderSearchHit(
                kind=ProviderEntityKind.TRACK,
                entity=make_track(
                    ProviderName.YOUTUBE,
                    "yt-track-1",
                    "Biography",
                    artist_names=["Кровосток"],
                    duration_ms=185000,
                ),
            ),
        ),
    ],
)
def test_ui_search_renders_results_and_explainability_for_explicit_kinds(
    sqlite_database_url: str,
    migrated_sqlite_database,
    kind: str,
    provider_search_hit: ProviderSearchHit,
) -> None:
    provider_registry = ProviderRegistry(
        (
            StubProvider(
                provider_name=ProviderName.YOUTUBE,
                search_hits=[provider_search_hit],
            ),
        )
    )

    with create_test_client(provider_registry=provider_registry, limiter=AllowAllLimiter()) as client:
        response = client.get("/ui", params={"q": "Кровосток", "kind": kind, "limit": 5})

    assert response.status_code == 200
    assert "Cross-platform matching without pretending certainty." in response.text
    assert "Results for" in response.text
    assert "features_json" in response.text


def test_static_app_script_no_longer_rewrites_ui_search_submit() -> None:
    with create_test_client(limiter=AllowAllLimiter()) as client:
        response = client.get("/static/app.js")

    assert response.status_code == 200
    assert 'document.body.dataset.autoRefreshSeconds' in response.text
    assert "window.location.reload();" in response.text
    assert 'addEventListener("submit"' not in response.text
    assert "FormData(form)" not in response.text
    assert "window.location.assign" not in response.text


def test_ui_search_accepts_empty_kind_query_as_any_without_js(
    sqlite_database_url: str,
    migrated_sqlite_database,
) -> None:
    with create_test_client(limiter=AllowAllLimiter()) as client:
        response = client.get("/ui", params={"q": "Кровосток", "kind": "", "limit": 10})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<option value='' selected>Any</option>" in response.text
    assert "Results for" in response.text
    assert "Search providers are not configured." not in response.text
    assert (
        "No merged results yet." in response.text
        or "features_json" in response.text
    )


def test_ui_search_normalizes_empty_kind_to_none_before_calling_search_service() -> None:
    mock_search_service = Mock()

    def build_response(*, query: str, kind: str | None, limit: int) -> SearchResponse:
        return SearchResponse(
            query=query,
            normalized_query="krovostok",
            kind=kind,
            partial=False,
            missing_platforms=[],
            cache=SearchCacheMetadata(status="miss"),
            results=[],
        )

    mock_search_service.search.side_effect = build_response

    with create_test_client(limiter=AllowAllLimiter()) as client:
        client.app.dependency_overrides[get_web_search_service] = lambda: mock_search_service

        empty_kind_response = client.get("/ui", params={"q": "Кровосток", "kind": "", "limit": 10})
        explicit_kind_response = client.get("/ui", params={"q": "Кровосток", "kind": "artist", "limit": 10})

    assert empty_kind_response.status_code == 200
    assert explicit_kind_response.status_code == 200
    assert mock_search_service.search.call_args_list == [
        call(query="Кровосток", kind=None, limit=10),
        call(query="Кровосток", kind="artist", limit=10),
    ]


def test_ui_search_with_default_public_yandex_registry_renders_search_page(
    sqlite_database_url: str,
    migrated_sqlite_database,
) -> None:
    with create_test_client(limiter=AllowAllLimiter()) as client:
        response = client.get("/ui", params={"q": "Кровосток", "kind": "artist", "limit": 5})

    assert response.status_code == 200
    assert "<option value='artist' selected>Artist</option>" in response.text
    assert "Results for" in response.text
    assert "Search providers are not configured." not in response.text
    assert (
        "No merged results yet." in response.text
        or "features_json" in response.text
    )


def test_ui_search_with_explicitly_empty_provider_registry_shows_notice(
    sqlite_database_url: str,
    migrated_sqlite_database,
) -> None:
    with create_test_client(
        provider_registry=ProviderRegistry(()),
        limiter=AllowAllLimiter(),
    ) as client:
        response = client.get("/ui", params={"q": "Кровосток", "kind": "artist", "limit": 5})

    assert response.status_code == 200
    assert "Search providers are not configured." in response.text
    assert "The UI is available, but live search is disabled." in response.text
    assert "<option value='artist' selected>Artist</option>" in response.text


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
    assert "Albums and releases" in artist_page.text
    assert "Missing on Yandex" in artist_page.text
    assert "Studio Session" in artist_page.text
    assert "no yandex" in artist_page.text
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
