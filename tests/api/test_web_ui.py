from __future__ import annotations

from unittest.mock import Mock, call

from app.api.deps import get_web_search_service
from app.api.schemas.search import (
    SearchCacheMetadata,
    SearchPlatformEntityPayload,
    SearchResponse,
    SearchResultItemPayload,
)
from app.db.models import LinkArtist, PlatformArtist
from app.db.repositories.artists import ArtistRepository
from app.providers import ProviderRegistry
from app.utils.normalization import display_norm, match_norm
from tests.test_support import (
    AllowAllLimiter,
    DenyAllLimiter,
    RecordingSyncScheduler,
    create_test_client,
    seed_catalog,
)


def _platform(
    provider: str,
    provider_id: str,
    kind: str,
    label: str,
    *,
    url: str | None = None,
    artist_names: list[str] | None = None,
    release_year: int | None = None,
    release_type: str | None = None,
    duration_ms: int | None = None,
    track_count: int | None = None,
) -> SearchPlatformEntityPayload:
    return SearchPlatformEntityPayload(
        provider=provider,
        provider_id=provider_id,
        kind=kind,
        label=label,
        display_norm=label.casefold(),
        match_norm=label.casefold(),
        url=url,
        artist_names=artist_names or [],
        release_year=release_year,
        release_type=release_type,
        duration_ms=duration_ms,
        track_count=track_count,
    )


def _response(kind: str, results: list[SearchResultItemPayload], *, missing_platforms: list[str] | None = None) -> SearchResponse:
    return SearchResponse(
        query="Кровосток",
        normalized_query="кровосток",
        kind=kind,
        partial=bool(missing_platforms),
        missing_platforms=missing_platforms or [],
        cache=SearchCacheMetadata(status="miss"),
        results=results,
    )


def test_root_redirects_to_ui_and_ui_landing_page_renders_without_providers() -> None:
    with create_test_client(limiter=AllowAllLimiter()) as client:
        redirect_response = client.get("/", follow_redirects=False)
        landing_response = client.get("/ui")

    assert redirect_response.status_code == 302
    assert redirect_response.headers["location"] == "/ui"

    assert landing_response.status_code == 200
    assert "data-ui-search-form='true'" in landing_response.text
    assert "Поиск музыки без лишнего шума" in landing_response.text
    assert "Нет в РФ" in landing_response.text
    assert "Cross-platform matching without pretending certainty." not in landing_response.text


def test_static_app_script_no_longer_rewrites_ui_search_submit() -> None:
    with create_test_client(limiter=AllowAllLimiter()) as client:
        response = client.get("/static/app.js")

    assert response.status_code == 200
    assert 'document.body.dataset.autoRefreshSeconds' in response.text
    assert "window.location.reload();" in response.text
    assert 'addEventListener("submit"' not in response.text
    assert "FormData(form)" not in response.text
    assert "window.location.assign" not in response.text


def test_ui_search_legacy_kind_renders_artist_tab_without_explicit_tab_param() -> None:
    mock_search_service = Mock()
    mock_search_service.search.return_value = _response(
        "artist",
        [
            SearchResultItemPayload(
                kind="artist",
                canonical_id=42,
                decision="auto",
                score=0.96,
                features_json={},
                platforms={
                    "youtube": _platform("youtube", "yt-artist-42", "artist", "Кровосток", url="https://youtube.test/artist-42"),
                    "yandex": _platform("yandex", "ya-artist-42", "artist", "Кровосток", url="https://yandex.test/artist-42"),
                },
            )
        ],
    )

    with create_test_client(limiter=AllowAllLimiter()) as client:
        client.app.dependency_overrides[get_web_search_service] = lambda: mock_search_service
        response = client.get("/ui", params={"q": "Кровосток", "kind": "artist", "limit": 10})

    assert response.status_code == 200
    assert mock_search_service.search.call_args_list == [call(query="Кровосток", kind="artist", limit=10)]
    assert "Исполнители" in response.text
    assert "tab=artist" in response.text


def test_ui_search_empty_kind_defaults_to_all_tab_and_calls_all_kinds() -> None:
    mock_search_service = Mock()
    mock_search_service.search.side_effect = lambda *, query, kind, limit: _response(kind, [])

    with create_test_client(limiter=AllowAllLimiter()) as client:
        client.app.dependency_overrides[get_web_search_service] = lambda: mock_search_service
        response = client.get("/ui", params={"q": "Кровосток", "kind": "", "limit": 10})

    assert response.status_code == 200
    assert mock_search_service.search.call_args_list == [
        call(query="Кровосток", kind="artist", limit=10),
        call(query="Кровосток", kind="release", limit=10),
        call(query="Кровосток", kind="track", limit=10),
    ]
    assert "tab=all" in response.text


def test_ui_search_tab_missing_calls_all_kinds() -> None:
    mock_search_service = Mock()
    mock_search_service.search.side_effect = lambda *, query, kind, limit: _response(kind, [])

    with create_test_client(limiter=AllowAllLimiter()) as client:
        client.app.dependency_overrides[get_web_search_service] = lambda: mock_search_service
        response = client.get("/ui", params={"q": "Кровосток", "tab": "missing", "limit": 5})

    assert response.status_code == 200
    assert mock_search_service.search.call_args_list == [
        call(query="Кровосток", kind="artist", limit=5),
        call(query="Кровосток", kind="release", limit=5),
        call(query="Кровосток", kind="track", limit=5),
    ]


def test_ui_search_track_tab_without_limit_requests_full_track_set() -> None:
    mock_search_service = Mock()
    mock_search_service.search.return_value = _response("track", [])

    with create_test_client(limiter=AllowAllLimiter()) as client:
        client.app.dependency_overrides[get_web_search_service] = lambda: mock_search_service
        response = client.get("/ui", params={"q": "Кровосток", "tab": "track"})

    assert response.status_code == 200
    assert mock_search_service.search.call_args_list == [call(query="Кровосток", kind="track", limit=None)]


def test_ui_search_all_tab_renders_featured_artist_and_grouped_sections() -> None:
    mock_search_service = Mock()
    responses = {
        "artist": _response(
            "artist",
            [
                SearchResultItemPayload(
                    kind="artist",
                    canonical_id=42,
                    decision="auto",
                    score=0.97,
                    features_json={"why": "best"},
                    platforms={
                        "youtube": _platform("youtube", "yt-artist-42", "artist", "Кровосток", url="https://youtube.test/artist-42"),
                        "yandex": _platform("yandex", "ya-artist-42", "artist", "Кровосток", url="https://yandex.test/artist-42"),
                    },
                ),
                SearchResultItemPayload(
                    kind="artist",
                    canonical_id=84,
                    decision="ambiguous",
                    score=0.72,
                    features_json={"why": "alt"},
                    platforms={
                        "youtube": _platform("youtube", "yt-artist-84", "artist", "Кровосток live", url="https://youtube.test/artist-84"),
                        "yandex": _platform("yandex", "ya-artist-84", "artist", "Кровосток live", url="https://yandex.test/artist-84"),
                    },
                ),
            ],
        ),
        "release": _response(
            "release",
            [
                SearchResultItemPayload(
                    kind="release",
                    canonical_id=12,
                    decision="auto",
                    score=0.89,
                    features_json={},
                    platforms={
                        "youtube": _platform(
                            "youtube",
                            "yt-release-12",
                            "release",
                            "Студийная сессия",
                            url="https://youtube.test/release-12",
                            artist_names=["Кровосток"],
                            release_year=2024,
                            release_type="album",
                            track_count=8,
                        ),
                        "yandex": _platform(
                            "yandex",
                            "ya-release-12",
                            "release",
                            "Студийная сессия",
                            url="https://yandex.test/release-12",
                            artist_names=["Кровосток"],
                            release_year=2024,
                            release_type="album",
                            track_count=8,
                        ),
                    },
                )
            ],
        ),
        "track": _response(
            "track",
            [
                SearchResultItemPayload(
                    kind="track",
                    canonical_id=index,
                    decision="ambiguous",
                    score=0.66,
                    features_json={},
                    platforms={
                        "youtube": _platform(
                            "youtube",
                            f"yt-track-{index}",
                            "track",
                            f"Биография {index}",
                            url=f"https://youtube.test/track-{index}",
                            artist_names=["Кровосток"],
                            duration_ms=185000,
                        ),
                        "yandex": _platform(
                            "yandex",
                            f"ya-track-{index}",
                            "track",
                            f"Биография {index}",
                            url=f"https://yandex.test/track-{index}",
                            artist_names=["Кровосток"],
                            duration_ms=185000,
                        ),
                    },
                )
                for index in range(1, 5)
            ],
        ),
    }
    mock_search_service.search.side_effect = lambda *, query, kind, limit: responses[kind]

    with create_test_client(limiter=AllowAllLimiter()) as client:
        client.app.dependency_overrides[get_web_search_service] = lambda: mock_search_service
        response = client.get("/ui", params={"q": "Кровосток", "tab": "all", "limit": 10})

    assert response.status_code == 200
    assert "data-featured-artist='true'" in response.text
    assert "Лучшее совпадение по исполнителю" in response.text
    assert "Кровосток live" in response.text
    assert "Исполнители" in response.text
    assert "Альбомы" in response.text
    assert "Треки" in response.text
    assert "Биография 4" in response.text
    assert "Yandex" in response.text
    assert "YouTube" in response.text
    assert "Технические детали поиска" not in response.text
    assert "Explainability" not in response.text


def test_ui_search_missing_tab_renders_humanized_missing_and_unconfirmed_sections() -> None:
    mock_search_service = Mock()
    responses = {
        "artist": _response(
            "artist",
            [
                SearchResultItemPayload(
                    kind="artist",
                    canonical_id=None,
                    decision="reject",
                    score=0.0,
                    features_json={"reason": "unmatched_provider_result"},
                    platforms={
                        "youtube": None,
                        "yandex": _platform("yandex", "ya-artist-1", "artist", "Кровосток архив", url="https://yandex.test/artist-1"),
                    },
                )
            ],
        ),
        "release": _response(
            "release",
            [
                SearchResultItemPayload(
                    kind="release",
                    canonical_id=None,
                    decision="reject",
                    score=0.25,
                    features_json={"reason": "low_confidence_match"},
                    platforms={
                        "youtube": _platform(
                            "youtube",
                            "yt-release-2",
                            "release",
                            "Не подтверждено",
                            url="https://youtube.test/release-2",
                            artist_names=["Кровосток"],
                            release_year=2014,
                            release_type="album",
                        ),
                        "yandex": _platform(
                            "yandex",
                            "ya-release-2",
                            "release",
                            "Не подтверждено",
                            url="https://yandex.test/release-2",
                            artist_names=["Кровосток"],
                            release_year=2014,
                            release_type="album",
                        ),
                    },
                )
            ],
        ),
        "track": _response(
            "track",
            [
                SearchResultItemPayload(
                    kind="track",
                    canonical_id=None,
                    decision="reject",
                    score=0.11,
                    features_json={"reason": "unmatched_provider_result"},
                    platforms={
                        "youtube": _platform(
                            "youtube",
                            "yt-track-2",
                            "track",
                            "Есть только на YouTube",
                            url="https://youtube.test/track-2",
                            artist_names=["Кровосток"],
                            duration_ms=201000,
                        ),
                        "yandex": None,
                    },
                )
            ],
        ),
    }
    mock_search_service.search.side_effect = lambda *, query, kind, limit: responses[kind]

    with create_test_client(limiter=AllowAllLimiter()) as client:
        client.app.dependency_overrides[get_web_search_service] = lambda: mock_search_service
        response = client.get("/ui", params={"q": "Кровосток", "tab": "missing", "limit": 10})

    assert response.status_code == 200
    assert "Есть на YouTube, не найдено на Yandex" in response.text
    assert "Совпадение на Yandex не подтверждено" in response.text
    assert "Есть только на YouTube" in response.text
    assert "Не подтверждено" in response.text
    assert "Кровосток архив" not in response.text


def test_ui_search_missing_tab_warns_when_yandex_status_is_unknown() -> None:
    mock_search_service = Mock()
    mock_search_service.search.side_effect = lambda *, query, kind, limit: _response(
        kind,
        [
            SearchResultItemPayload(
                kind=kind,
                canonical_id=None,
                decision="reject",
                score=0.1,
                features_json={},
                platforms={
                    "youtube": _platform("youtube", f"yt-{kind}-1", kind, f"{kind}-title"),
                    "yandex": None,
                },
            )
        ],
        missing_platforms=["yandex"],
    )

    with create_test_client(limiter=AllowAllLimiter()) as client:
        client.app.dependency_overrides[get_web_search_service] = lambda: mock_search_service
        response = client.get("/ui", params={"q": "Кровосток", "tab": "missing", "limit": 10})

    assert response.status_code == 200
    assert "не удалось проверить Yandex" in response.text
    assert "Подтвержденных YouTube-only результатов по этому запросу нет." in response.text


def test_ui_search_with_explicitly_empty_provider_registry_shows_notice() -> None:
    with create_test_client(
        provider_registry=ProviderRegistry(()),
        limiter=AllowAllLimiter(),
    ) as client:
        response = client.get("/ui", params={"q": "Кровосток", "tab": "artist", "limit": 5})

    assert response.status_code == 200
    assert "Поиск сейчас недоступен" in response.text
    assert "Исполнители" in response.text


def test_ui_artist_page_renders_availability_catalog_and_missing_on_yandex_views(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    ids = seed_catalog(db_session, include_yandex_catalog_sections=True)

    with create_test_client(limiter=AllowAllLimiter()) as client:
        response = client.get(f"/ui/artists/{ids['artist_id']}")

    assert response.status_code == 200
    assert "Есть на Yandex и YouTube." in response.text
    assert "Где доступно" in response.text
    assert "Что есть в каталоге Yandex" in response.text
    assert "Нет на Yandex" in response.text
    assert "Есть кандидат на Yandex" in response.text
    assert "Технические детали" not in response.text


def test_ui_release_and_track_pages_render_product_availability_blocks(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    ids = seed_catalog(db_session)

    with create_test_client(limiter=AllowAllLimiter()) as client:
        release_page = client.get(f"/ui/releases/{ids['release_id']}")
        track_page = client.get(f"/ui/tracks/{ids['track_id']}")

    assert release_page.status_code == 200
    assert "Есть на YouTube, но подтвержденной карточки на Yandex нет." in release_page.text
    assert "Нет на Yandex" in release_page.text
    assert "Треклист" in release_page.text
    assert "Технические детали" not in release_page.text

    assert track_page.status_code == 200
    assert "Есть на Yandex и YouTube." in track_page.text
    assert "Где доступно" in track_page.text
    assert "Релизы" in track_page.text


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
    assert "Где доступно" in artist_page.text
    assert "Релизы" in artist_page.text
    assert "Нет на Yandex" in artist_page.text
    assert "JSON API" not in artist_page.text

    assert sync_response.status_code == 303
    assert "/ui/jobs/" in sync_response.headers["location"]

    assert job_page.status_code == 200
    assert "Обновление" in job_page.text
    assert "queued" in job_page.text


def test_ui_artist_page_shows_fill_state_when_only_platform_links_exist(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    artist = ArtistRepository(db_session).create(
        display_name="AC/DC",
        display_norm=display_norm("AC/DC"),
        match_norm=match_norm("AC/DC"),
    )
    youtube = PlatformArtist(
        platform="youtube",
        platform_id="yt-acdc",
        display_name="AC/DC",
        display_norm=display_norm("AC/DC"),
        match_norm=match_norm("AC/DC"),
        raw_json={},
    )
    yandex = PlatformArtist(
        platform="yandex",
        platform_id="ya-acdc",
        display_name="AC/DC",
        display_norm=display_norm("AC/DC"),
        match_norm=match_norm("AC/DC"),
        raw_json={},
    )
    db_session.add_all(
        [
            youtube,
            yandex,
            LinkArtist(artist=artist, platform_artist=youtube, decision="auto", score=1.0, features_json={}),
            LinkArtist(artist=artist, platform_artist=yandex, decision="auto", score=1.0, features_json={}),
        ]
    )
    db_session.commit()

    with create_test_client(limiter=AllowAllLimiter()) as client:
        response = client.get(f"/ui/artists/{artist.id}")

    assert response.status_code == 200
    assert "Карточка «AC/DC» ещё наполняется" not in response.text
    assert "Где доступно" in response.text
    assert "Релизы" not in response.text
    assert "Треки" not in response.text
    assert "Варианты названия" not in response.text


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
