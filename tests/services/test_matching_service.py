from __future__ import annotations

from app.providers.base import ProviderArtist, ProviderName, ProviderRelease, ProviderTrack
from app.services.matching_service import MatchingConfig, MatchingService
from app.utils.normalization import display_norm, match_norm


def make_artist(provider: ProviderName, provider_id: str, name: str, aliases: list[str] | None = None) -> ProviderArtist:
    aliases = aliases or []
    return ProviderArtist(
        provider=provider,
        provider_id=provider_id,
        name=name,
        display_norm=display_norm(name),
        match_norm=match_norm(name),
        aliases=aliases,
        alias_match_norms=[match_norm(alias) for alias in aliases],
    )


def make_release(
    provider: ProviderName,
    provider_id: str,
    title: str,
    artists: list[str],
    *,
    release_year: int | None = None,
    track_count: int | None = None,
) -> ProviderRelease:
    from app.utils.version_tags import extract_version_tags

    return ProviderRelease(
        provider=provider,
        provider_id=provider_id,
        title=title,
        display_norm=display_norm(title),
        match_norm=match_norm(title),
        artist_names=artists,
        artist_match_norms=[match_norm(artist) for artist in artists],
        release_year=release_year,
        track_count=track_count,
        version_tags_json=extract_version_tags(title),
    )


def make_track(
    provider: ProviderName,
    provider_id: str,
    title: str,
    artists: list[str],
    *,
    duration_ms: int | None = None,
    release_title: str | None = None,
) -> ProviderTrack:
    from app.utils.version_tags import extract_version_tags

    return ProviderTrack(
        provider=provider,
        provider_id=provider_id,
        title=title,
        display_norm=display_norm(title),
        match_norm=match_norm(title),
        artist_names=artists,
        artist_match_norms=[match_norm(artist) for artist in artists],
        duration_ms=duration_ms,
        version_tags_json=extract_version_tags(title),
        release_title=release_title,
        release_match_norm=match_norm(release_title or "") or None,
    )


def test_artist_matching_auto_matches_transliterated_alias() -> None:
    service = MatchingService(MatchingConfig(0.35, 0.6, 0.88, 0.05))
    subject = make_artist(ProviderName.YOUTUBE, "yt-1", "Кровосток")
    candidates = [
        make_artist(ProviderName.YANDEX, "ya-1", "Krovostok"),
        make_artist(ProviderName.YANDEX, "ya-2", "Molchat Doma"),
    ]

    result = service.match_artists(subject, candidates)

    assert result.decision == "auto"
    assert result.matched_candidate is not None
    assert result.matched_candidate.provider_id == "ya-1"
    assert result.score >= 0.88


def test_release_matching_prefers_ambiguous_when_version_conflicts() -> None:
    service = MatchingService(MatchingConfig(0.35, 0.6, 0.88, 0.05))
    subject = make_release(
        ProviderName.YOUTUBE,
        "yt-rel-1",
        "Тестовый альбом (Live)",
        ["Исполнитель"],
        release_year=2023,
        track_count=10,
    )
    candidates = [
        make_release(
            ProviderName.YANDEX,
            "ya-rel-1",
            "Testovyi albom (Remix)",
            ["Ispolnitel"],
            release_year=2023,
            track_count=10,
        )
    ]

    result = service.match_releases(subject, candidates)

    assert result.decision == "ambiguous"
    assert result.matched_candidate is not None
    assert result.features_json["version_conflicts"] == ["live", "remix"]
    assert "version_conflict" in result.features_json["decision_reasons"]


def test_track_matching_rejects_large_duration_mismatch() -> None:
    service = MatchingService(MatchingConfig(0.35, 0.6, 0.88, 0.05))
    subject = make_track(
        ProviderName.YOUTUBE,
        "yt-tr-1",
        "Говорит Москва",
        ["Shortparis"],
        duration_ms=200000,
        release_title="Так закалялась сталь",
    )
    candidates = [
        make_track(
            ProviderName.YANDEX,
            "ya-tr-1",
            "Govorit Moskva",
            ["Shortparis"],
            duration_ms=310000,
            release_title="Так закалялась сталь",
        )
    ]

    result = service.match_tracks(subject, candidates)

    assert result.decision == "reject"
    assert result.matched_candidate is None
    assert result.considered_candidates[0].score < 0.6


def test_matching_marks_close_top_candidates_as_ambiguous() -> None:
    service = MatchingService(MatchingConfig(0.35, 0.6, 0.88, 0.05))
    subject = make_artist(ProviderName.YOUTUBE, "yt-1", "Motorama")
    candidates = [
        make_artist(ProviderName.YANDEX, "ya-1", "Motorama"),
        make_artist(ProviderName.YANDEX, "ya-2", "Motorama"),
    ]

    result = service.match_artists(subject, candidates)

    assert result.decision == "ambiguous"
    assert result.matched_candidate is not None
    assert "top_gap_too_small" in result.features_json["decision_reasons"]
    assert len(result.considered_candidates) == 2


def test_matching_features_are_reproducible() -> None:
    service = MatchingService(MatchingConfig(0.35, 0.6, 0.88, 0.05))
    subject = make_release(
        ProviderName.YOUTUBE,
        "yt-rel-1",
        "Этажи",
        ["Molchat Doma"],
        release_year=2018,
        track_count=11,
    )
    candidates = [
        make_release(
            ProviderName.YANDEX,
            "ya-rel-1",
            "Etazhi",
            ["Molchat Doma"],
            release_year=2018,
            track_count=11,
        )
    ]

    first = service.match_releases(subject, candidates)
    second = service.match_releases(subject, candidates)

    assert first.score == second.score
    assert first.features_json == second.features_json
