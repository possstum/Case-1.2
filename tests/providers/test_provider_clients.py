from __future__ import annotations

import json
from urllib.request import Request

from app.providers import ProviderEntityKind
from app.providers.youtube_music.client import YouTubeMusicClient
from app.providers.yandex_music.client import YandexMusicClient


class DummyResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "DummyResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_youtube_client_uses_configured_timeout(monkeypatch) -> None:
    seen_timeouts: list[float] = []

    def fake_urlopen(url, *, timeout: float):
        seen_timeouts.append(timeout)
        return DummyResponse({"items": []})

    monkeypatch.setattr("app.providers.youtube_music.client.urlopen", fake_urlopen)

    client = YouTubeMusicClient(token="youtube-token", timeout_seconds=7.5)
    client.search("Motorama", limit=1, kind=ProviderEntityKind.ARTIST)

    assert seen_timeouts == [7.5]


def test_yandex_client_uses_configured_timeout(monkeypatch) -> None:
    seen_timeouts: list[float] = []
    seen_targets: list[object] = []

    def fake_urlopen(target, *, timeout: float):
        seen_targets.append(target)
        seen_timeouts.append(timeout)
        return DummyResponse({"result": {"artists": {"results": []}}})

    monkeypatch.setattr("app.providers.yandex_music.client.urlopen", fake_urlopen)

    client = YandexMusicClient(token="yandex-token", timeout_seconds=6.25)
    client.search("Motorama", limit=1, kind=ProviderEntityKind.ARTIST)

    assert seen_timeouts == [6.25]
    assert isinstance(seen_targets[0], str)


def test_yandex_client_search_uses_public_route_without_auth_even_when_token_present(monkeypatch) -> None:
    seen_requests: list[tuple[str, dict[str, str], float]] = []

    def fake_urlopen(target, *, timeout: float):
        if isinstance(target, Request):
            seen_requests.append((target.full_url, dict(target.header_items()), timeout))
        else:
            seen_requests.append((target, {}, timeout))
        return DummyResponse(
            {
                "result": {
                    "artists": {
                        "results": [
                            {
                                "id": 4065,
                                "name": "Taylor Swift",
                                "decomposed": [],
                            }
                        ]
                    }
                }
            }
        )

    monkeypatch.setattr("app.providers.yandex_music.client.urlopen", fake_urlopen)

    client = YandexMusicClient(token="yandex-token")
    result = client.search("Taylor Swift", limit=1, kind=ProviderEntityKind.ARTIST)

    assert len(result.items) == 1
    assert result.items[0].entity.provider_id == "4065"
    assert seen_requests == [
        (
            "https://api.music.yandex.net/search?text=Taylor+Swift&page=0&type=artist&nocorrect=false&page-size=1",
            {},
            5.0,
        )
    ]


def test_yandex_client_search_does_not_require_token(monkeypatch) -> None:
    def fake_urlopen(target, *, timeout: float):
        assert target == (
            "https://api.music.yandex.net/search?text=Taylor+Swift&page=0&type=artist&nocorrect=false&page-size=1"
        )
        assert timeout == 5.0
        return DummyResponse(
            {
                "result": {
                    "artists": {
                        "results": [
                            {
                                "id": 4065,
                                "name": "Taylor Swift",
                                "decomposed": [],
                            }
                        ]
                    }
                }
            }
        )

    monkeypatch.setattr("app.providers.yandex_music.client.urlopen", fake_urlopen)

    client = YandexMusicClient()
    result = client.search("Taylor Swift", limit=1, kind=ProviderEntityKind.ARTIST)

    assert len(result.items) == 1
    assert result.items[0].entity.provider_id == "4065"


def test_yandex_client_get_artist_uses_public_artist_detail_route(monkeypatch) -> None:
    seen_requests: list[tuple[str, dict[str, str], float]] = []

    def fake_urlopen(target, *, timeout: float):
        if isinstance(target, Request):
            seen_requests.append((target.full_url, dict(target.header_items()), timeout))
        else:
            seen_requests.append((target, {}, timeout))
        return DummyResponse(
            {
                "result": {
                    "artist": {
                        "id": 1014281,
                        "name": "Motorama",
                        "dbAliases": ["Моторама"],
                    },
                    "albums": [
                        {
                            "id": 8460751,
                            "title": "Motorama EP",
                            "artists": [{"name": "Motorama"}],
                            "year": 2014,
                            "trackCount": 2,
                        }
                    ],
                    "popularTracks": [
                        {
                            "id": 119728832,
                            "title": "Motorama",
                            "artists": [{"name": "Motorama"}],
                            "durationMs": 150890,
                            "albums": [
                                {
                                    "id": 8460751,
                                    "title": "Motorama EP",
                                    "trackPosition": {"index": 1, "volume": 1},
                                }
                            ],
                        }
                    ],
                    "similarArtists": [{"id": 99, "name": "Human Tetris"}],
                }
            }
        )

    monkeypatch.setattr("app.providers.yandex_music.client.urlopen", fake_urlopen)

    client = YandexMusicClient(timeout_seconds=4.5)
    artist = client.get_artist("1014281")

    assert artist.provider_id == "1014281"
    assert artist.name == "Motorama"
    assert artist.aliases == ["Моторама"]
    assert seen_requests == [("https://api.music.yandex.net/artists/1014281", {}, 4.5)]


def test_yandex_client_get_artist_brief_info_maps_lists_and_stats(monkeypatch) -> None:
    def fake_urlopen(target, *, timeout: float):
        assert target == "https://api.music.yandex.net/artists/1014281/brief-info"
        assert timeout == 5.0
        return DummyResponse(
            {
                "result": {
                    "artist": {"id": 1014281, "name": "Motorama"},
                    "albums": [
                        {
                            "id": 8460751,
                            "title": "Motorama EP",
                            "artists": [{"name": "Motorama"}],
                            "year": 2014,
                            "trackCount": 2,
                        }
                    ],
                    "alsoAlbums": [
                        {
                            "id": 999,
                            "title": "Compilation Feature",
                            "artists": [{"name": "Motorama"}],
                        }
                    ],
                    "popularTracks": [
                        {
                            "id": 119728832,
                            "title": "Motorama",
                            "artists": [{"name": "Motorama"}],
                            "durationMs": 150890,
                        }
                    ],
                    "similarArtists": [{"id": 102, "name": "Ploho"}],
                    "stats": {"tracks": 24},
                    "playlistIds": [11, "12"],
                    "playlists": [{"uid": "pl-1", "title": "Yandex Mix"}],
                    "links": [{"title": "Wiki", "url": "https://example.com/motorama"}],
                    "hasTrailer": True,
                }
            }
        )

    monkeypatch.setattr("app.providers.yandex_music.client.urlopen", fake_urlopen)

    client = YandexMusicClient()
    payload = client.get_artist_brief_info("1014281")

    assert payload.artist.id == "1014281"
    assert payload.albums[0].id == "8460751"
    assert payload.also_albums[0].id == "999"
    assert payload.popular_tracks[0].id == "119728832"
    assert payload.similar_artists[0].name == "Ploho"
    assert payload.stats == {"tracks": 24}
    assert payload.playlist_ids == ["11", "12"]
    assert payload.playlists[0].id == "pl-1"
    assert payload.links[0].url == "https://example.com/motorama"
    assert payload.has_trailer is True


def test_yandex_client_get_artist_direct_albums_maps_pager(monkeypatch) -> None:
    def fake_urlopen(target, *, timeout: float):
        assert target == (
            "https://api.music.yandex.net/artists/1014281/direct-albums?page=1&page-size=2"
        )
        assert timeout == 5.0
        return DummyResponse(
            {
                "result": {
                    "pager": {"page": 1, "perPage": 2, "total": 24},
                    "albums": [
                        {
                            "id": 8460751,
                            "title": "Motorama EP",
                            "artists": [{"name": "Motorama"}],
                            "year": 2014,
                            "trackCount": 2,
                            "type": "ep",
                        }
                    ],
                }
            }
        )

    monkeypatch.setattr("app.providers.yandex_music.client.urlopen", fake_urlopen)

    client = YandexMusicClient()
    payload = client.get_artist_direct_albums("1014281", page=1, page_size=2)

    assert payload.artist_id == "1014281"
    assert payload.pager is not None
    assert payload.pager.page == 1
    assert payload.pager.per_page == 2
    assert payload.pager.total == 24
    assert payload.albums[0].id == "8460751"
    assert payload.albums[0].release_type == "ep"


def test_yandex_client_get_artist_tracks_maps_track_page(monkeypatch) -> None:
    def fake_urlopen(target, *, timeout: float):
        assert target == "https://api.music.yandex.net/artists/1014281/tracks?page=0&page-size=1"
        assert timeout == 5.0
        return DummyResponse(
            {
                "result": {
                    "pager": {"page": 0, "perPage": 1, "total": 20},
                    "tracks": [
                        {
                            "id": 119728832,
                            "title": "Motorama",
                            "artists": [{"name": "Motorama"}],
                            "durationMs": 150890,
                            "albums": [
                                {
                                    "id": 28413817,
                                    "title": "UGLYCAT",
                                    "trackPosition": {"index": 2, "volume": 1},
                                }
                            ],
                        }
                    ],
                }
            }
        )

    monkeypatch.setattr("app.providers.yandex_music.client.urlopen", fake_urlopen)

    client = YandexMusicClient()
    payload = client.get_artist_tracks("1014281", page=0, page_size=1)

    assert payload.artist_id == "1014281"
    assert payload.pager is not None
    assert payload.pager.total == 20
    assert payload.tracks[0].id == "119728832"
    assert payload.tracks[0].release_title == "UGLYCAT"
    assert payload.tracks[0].track_number == 2


def test_yandex_client_get_release_maps_album_detail(monkeypatch) -> None:
    def fake_urlopen(target, *, timeout: float):
        assert target == "https://api.music.yandex.net/albums/8460751"
        assert timeout == 5.0
        return DummyResponse(
            {
                "result": {
                    "id": 8460751,
                    "title": "Motorama EP",
                    "artists": [{"name": "Motorama"}],
                    "year": 2014,
                    "trackCount": 2,
                    "type": "ep",
                }
            }
        )

    monkeypatch.setattr("app.providers.yandex_music.client.urlopen", fake_urlopen)

    client = YandexMusicClient()
    release = client.get_release("8460751")

    assert release.provider_id == "8460751"
    assert release.title == "Motorama EP"
    assert release.release_type == "ep"
    assert release.release_year == 2014
    assert release.track_count == 2


def test_yandex_client_get_release_with_tracks_maps_ordered_volumes(monkeypatch) -> None:
    def fake_urlopen(target, *, timeout: float):
        assert target == "https://api.music.yandex.net/albums/8460751/with-tracks"
        assert timeout == 5.0
        return DummyResponse(
            {
                "result": {
                    "id": 8460751,
                    "title": "Motorama EP",
                    "artists": [{"name": "Motorama"}],
                    "year": 2014,
                    "trackCount": 2,
                    "pager": {"page": 0, "perPage": 2, "total": 2},
                    "volumes": [
                        [
                            {
                                "id": 56853139,
                                "title": "Motorama",
                                "artists": [{"name": "Motorama"}],
                                "durationMs": 150890,
                                "albums": [
                                    {
                                        "id": 8460751,
                                        "title": "Motorama EP",
                                        "trackPosition": {"index": 1, "volume": 1},
                                    }
                                ],
                            },
                            {
                                "id": 56853140,
                                "title": "Ghost",
                                "artists": [{"name": "Motorama"}],
                                "durationMs": 171000,
                                "albums": [
                                    {
                                        "id": 8460751,
                                        "title": "Motorama EP",
                                        "trackPosition": {"index": 2, "volume": 1},
                                    }
                                ],
                            },
                        ]
                    ],
                }
            }
        )

    monkeypatch.setattr("app.providers.yandex_music.client.urlopen", fake_urlopen)

    client = YandexMusicClient()
    payload = client.get_release_with_tracks("8460751")

    assert payload.release.id == "8460751"
    assert payload.release.track_count == 2
    assert payload.pager is not None
    assert payload.pager.total == 2
    assert len(payload.volumes) == 1
    assert [track.track_number for track in payload.volumes[0]] == [1, 2]
    assert [track.disc_number for track in payload.volumes[0]] == [1, 1]
    assert payload.volumes[0][0].release_title == "Motorama EP"


def test_yandex_client_get_track_maps_nested_album_track_position(monkeypatch) -> None:
    def fake_urlopen(target, *, timeout: float):
        assert target == "https://api.music.yandex.net/tracks/119728832"
        assert timeout == 5.0
        return DummyResponse(
            {
                "result": [
                    {
                        "id": 119728832,
                        "title": "Motorama",
                        "artists": [{"name": "Motorama"}],
                        "durationMs": 150890,
                        "albums": [
                            {
                                "id": 28413817,
                                "title": "UGLYCAT",
                                "trackPosition": {"index": 2, "volume": 1},
                            }
                        ],
                    }
                ]
            }
        )

    monkeypatch.setattr("app.providers.yandex_music.client.urlopen", fake_urlopen)

    client = YandexMusicClient()
    track = client.get_track("119728832")

    assert track.provider_id == "119728832"
    assert track.duration_ms == 150890
    assert track.release_title == "UGLYCAT"
    assert track.track_number == 2
