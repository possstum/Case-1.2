from __future__ import annotations

from app.api.schemas.search import (
    SearchCacheMetadata,
    SearchPlatformEntityPayload,
    SearchResponse,
    SearchResultItemPayload,
)
from app.web.presenters import build_search_page_view, requested_kinds_for_tab, resolve_search_tab


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
    )


def _response(kind: str, results: list[SearchResultItemPayload], *, missing_platforms: list[str] | None = None) -> SearchResponse:
    return SearchResponse(
        query="маваши",
        normalized_query="маваши",
        kind=kind,
        partial=bool(missing_platforms),
        missing_platforms=missing_platforms or [],
        cache=SearchCacheMetadata(status="miss"),
        results=results,
    )


def test_resolve_search_tab_uses_tab_then_legacy_kind_then_all() -> None:
    assert resolve_search_tab("missing", "artist") == "missing"
    assert resolve_search_tab(None, "artist") == "artist"
    assert resolve_search_tab(None, None) == "all"


def test_requested_kinds_for_tab_expands_all_and_missing() -> None:
    assert requested_kinds_for_tab("all") == ("artist", "release", "track")
    assert requested_kinds_for_tab("missing") == ("artist", "release", "track")
    assert requested_kinds_for_tab("artist") == ("artist",)


def test_build_search_page_view_classifies_missing_results() -> None:
    youtube_only = SearchResultItemPayload(
        kind="track",
        canonical_id=None,
        decision="reject",
        score=0.13,
        features_json={"reason": "unmatched_provider_result"},
        platforms={
            "youtube": _platform(
                "youtube",
                "yt-track-1",
                "track",
                "Пуля",
                url="https://youtube.test/track-1",
                artist_names=["Маваши"],
                duration_ms=191000,
            ),
            "yandex": None,
        },
    )
    unconfirmed = SearchResultItemPayload(
        kind="release",
        canonical_id=None,
        decision="reject",
        score=0.21,
        features_json={"reason": "low_confidence_match"},
        platforms={
            "youtube": _platform(
                "youtube",
                "yt-release-1",
                "release",
                "Сила в правде",
                url="https://youtube.test/release-1",
                artist_names=["Маваши"],
                release_year=2015,
                release_type="album",
            ),
            "yandex": _platform(
                "yandex",
                "ya-release-1",
                "release",
                "Сила в правде",
                url="https://yandex.test/release-1",
                artist_names=["Маваши"],
                release_year=2015,
                release_type="album",
            ),
        },
    )
    yandex_only = SearchResultItemPayload(
        kind="artist",
        canonical_id=None,
        decision="reject",
        score=0.0,
        features_json={"reason": "unmatched_provider_result"},
        platforms={
            "youtube": None,
            "yandex": _platform("yandex", "ya-artist-only", "artist", "Маваши архив", url="https://yandex.test/artist-only"),
        },
    )

    view = build_search_page_view(
        query="маваши",
        active_tab="missing",
        limit=5,
        responses_by_kind={
            "artist": _response("artist", [yandex_only]),
            "release": _response("release", [unconfirmed]),
            "track": _response("track", [youtube_only]),
        },
    )

    sections = {section.key: section for section in view.sections}
    assert [card.title for card in sections["youtube-only"].items] == ["Пуля"]
    assert [card.title for card in sections["unconfirmed-yandex"].items] == ["Сила в правде"]
    assert all(card.title != "Маваши архив" for section in view.sections for card in section.items)


def test_build_search_page_view_marks_yandex_unavailable_as_unknown_not_missing() -> None:
    youtube_only = SearchResultItemPayload(
        kind="track",
        canonical_id=None,
        decision="reject",
        score=0.11,
        features_json={},
        platforms={
            "youtube": _platform("youtube", "yt-track-2", "track", "Свой путь", artist_names=["Маваши"]),
            "yandex": None,
        },
    )

    view = build_search_page_view(
        query="маваши",
        active_tab="missing",
        limit=5,
        responses_by_kind={
            "track": _response("track", [youtube_only], missing_platforms=["yandex"]),
        },
    )

    assert all(not section.items for section in view.sections)
    assert any("не удалось проверить Yandex" in notice.text for notice in view.notices)


def test_build_search_page_view_exposes_human_status_badges_for_regular_tabs() -> None:
    confirmed = SearchResultItemPayload(
        kind="artist",
        canonical_id=1,
        decision="auto",
        score=0.97,
        features_json={},
        platforms={
            "youtube": _platform("youtube", "yt-artist-1", "artist", "Маваши"),
            "yandex": _platform("yandex", "ya-artist-1", "artist", "Маваши"),
        },
    )
    ambiguous = SearchResultItemPayload(
        kind="artist",
        canonical_id=2,
        decision="ambiguous",
        score=0.64,
        features_json={},
        platforms={
            "youtube": _platform("youtube", "yt-artist-2", "artist", "Маваши live"),
            "yandex": _platform("yandex", "ya-artist-2", "artist", "Маваши Live"),
        },
    )

    view = build_search_page_view(
        query="маваши",
        active_tab="artist",
        limit=5,
        responses_by_kind={"artist": _response("artist", [confirmed, ambiguous])},
    )

    badges_by_title = {
        card.title: [badge.label for badge in card.badges]
        for card in view.sections[0].items
    }
    assert "Подтверждено" in badges_by_title["Маваши"]
    assert "Возможный вариант" in badges_by_title["Маваши Live"]


def test_build_search_page_view_all_tab_keeps_full_track_list() -> None:
    tracks = [
        SearchResultItemPayload(
            kind="track",
            canonical_id=index,
            decision="auto",
            score=0.9,
            features_json={},
            platforms={
                "youtube": _platform(
                    "youtube",
                    f"yt-track-{index}",
                    "track",
                    f"Трек {index}",
                    artist_names=["Маваши"],
                ),
                "yandex": _platform(
                    "yandex",
                    f"ya-track-{index}",
                    "track",
                    f"Трек {index}",
                    artist_names=["Маваши"],
                ),
            },
        )
        for index in range(1, 5)
    ]

    view = build_search_page_view(
        query="маваши",
        active_tab="all",
        limit=None,
        responses_by_kind={"track": _response("track", tracks)},
    )

    tracks_section = next(section for section in view.sections if section.key == "tracks")
    assert [card.title for card in tracks_section.items] == ["Трек 1", "Трек 2", "Трек 3", "Трек 4"]
