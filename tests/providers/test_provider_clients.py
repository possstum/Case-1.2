from __future__ import annotations

import json

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

    def fake_urlopen(request, *, timeout: float):
        seen_timeouts.append(timeout)
        return DummyResponse({"result": {"artists": {"results": []}}})

    monkeypatch.setattr("app.providers.yandex_music.client.urlopen", fake_urlopen)

    client = YandexMusicClient(token="yandex-token", timeout_seconds=6.25)
    client.search("Motorama", limit=1, kind=ProviderEntityKind.ARTIST)

    assert seen_timeouts == [6.25]
