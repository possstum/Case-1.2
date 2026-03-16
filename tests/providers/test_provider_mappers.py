from app.providers.base import ProviderName
from app.providers.youtube_music.mapper import (
    map_artist as map_youtube_artist,
    map_release as map_youtube_release,
)
from app.providers.youtube_music.schemas import (
    YouTubeMusicArtistPayload,
    YouTubeMusicReleasePayload,
)
from app.providers.yandex_music.mapper import map_track as map_yandex_track
from app.providers.yandex_music.schemas import YandexMusicTrackPayload


def test_youtube_artist_mapper_builds_normalized_provider_entity() -> None:
    payload = YouTubeMusicArtistPayload(id="yt-1", name="Кровосток", aliases=["Krovostok"])

    artist = map_youtube_artist(payload)

    assert artist.provider == ProviderName.YOUTUBE
    assert artist.display_norm == "кровосток"
    assert artist.match_norm == "krovostok"
    assert artist.alias_match_norms == ["krovostok"]


def test_youtube_release_mapper_extracts_version_tags() -> None:
    payload = YouTubeMusicReleasePayload(
        id="yt-rel-1",
        title="Тестовый альбом (Deluxe)",
        artists=["Исполнитель"],
        year=2023,
        track_count=10,
    )

    release = map_youtube_release(payload)

    assert release.version_tags_json == ["deluxe"]
    assert release.artist_match_norms == ["ispolnitel"]


def test_yandex_track_mapper_sets_release_norm_and_duration() -> None:
    payload = YandexMusicTrackPayload(
        id="ya-tr-1",
        title="Говорит Москва",
        artists=["Shortparis"],
        duration_ms=203000,
        release_title="Так закалялась сталь",
        track_number=1,
    )

    track = map_yandex_track(payload)

    assert track.provider == ProviderName.YANDEX
    assert track.release_match_norm == "tak zakalyalas stal"
    assert track.duration_ms == 203000
