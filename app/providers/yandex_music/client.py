from __future__ import annotations

import json
from typing import Any, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.providers.yandex_music.mapper import map_artist, map_release, map_track
from app.providers.yandex_music.schemas import (
    YandexMusicArtistPayload,
    YandexMusicReleasePayload,
    YandexMusicTrackPayload,
)

from app.providers.base import (
    MusicProvider,
    ProviderArtist,
    ProviderEntityKind,
    ProviderName,
    ProviderRelease,
    ProviderSearchHit,
    ProviderSearchResult,
    ProviderTrack,
)


class YandexMusicClient(MusicProvider):
    provider_name = ProviderName.YANDEX
    _base_url = "https://api.music.yandex.net/search"

    def __init__(self, *, token: Optional[str] = None, timeout_seconds: float = 5.0) -> None:
        self.token = token
        self.timeout_seconds = timeout_seconds

    def search(
        self,
        query: str,
        *,
        limit: int,
        kind: Optional[ProviderEntityKind] = None,
    ) -> ProviderSearchResult:
        if not self.token:
            return ProviderSearchResult(query=query)

        items: list[ProviderSearchHit] = []
        for resolved_kind in self._resolve_kinds(kind):
            params = {
                "text": query,
                "page": "0",
                "type": self._search_type_for_kind(resolved_kind),
                "nocorrect": "false",
                "page-size": str(limit),
            }
            payload = self._get_json(self._base_url, params=params)
            items.extend(self._map_search_items(resolved_kind, payload))
        return ProviderSearchResult(query=query, items=items[:limit])

    def get_artist(self, provider_id: str) -> ProviderArtist:
        raise NotImplementedError("Yandex Music provider integration is not implemented yet")

    def get_release(self, provider_id: str) -> ProviderRelease:
        raise NotImplementedError("Yandex Music provider integration is not implemented yet")

    def get_track(self, provider_id: str) -> ProviderTrack:
        raise NotImplementedError("Yandex Music provider integration is not implemented yet")

    def _get_json(self, url: str, *, params: dict[str, str]) -> dict[str, Any]:
        request = Request(
            f"{url}?{urlencode(params)}",
            headers={"Authorization": f"OAuth {self.token}"},
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _resolve_kinds(
        self,
        kind: Optional[ProviderEntityKind],
    ) -> tuple[ProviderEntityKind, ...]:
        if kind is not None:
            return (kind,)
        return (
            ProviderEntityKind.ARTIST,
            ProviderEntityKind.RELEASE,
            ProviderEntityKind.TRACK,
        )

    def _search_type_for_kind(self, kind: ProviderEntityKind) -> str:
        if kind == ProviderEntityKind.ARTIST:
            return "artist"
        if kind == ProviderEntityKind.RELEASE:
            return "album"
        return "track"

    def _map_search_items(
        self,
        kind: ProviderEntityKind,
        payload: dict[str, Any],
    ) -> list[ProviderSearchHit]:
        result = payload.get("result", {})
        key = {
            ProviderEntityKind.ARTIST: "artists",
            ProviderEntityKind.RELEASE: "albums",
            ProviderEntityKind.TRACK: "tracks",
        }[kind]
        section = result.get(key) or {}
        results = section.get("results") or []

        mapped: list[ProviderSearchHit] = []
        for item in results:
            hit = self._map_search_item(kind, item)
            if hit is not None:
                mapped.append(hit)
        return mapped

    def _map_search_item(
        self,
        kind: ProviderEntityKind,
        item: dict[str, Any],
    ) -> ProviderSearchHit | None:
        provider_id = item.get("id")
        if provider_id is None:
            return None
        provider_id = str(provider_id)

        if kind == ProviderEntityKind.ARTIST:
            name = item.get("name")
            if not name:
                return None
            aliases = [alias for alias in item.get("decomposed", []) if isinstance(alias, str)]
            payload = YandexMusicArtistPayload(
                id=provider_id,
                name=name,
                aliases=aliases,
                url=f"https://music.yandex.ru/artist/{provider_id}",
                raw_json=item,
            )
            return ProviderSearchHit(kind=kind, entity=map_artist(payload))

        if kind == ProviderEntityKind.RELEASE:
            title = item.get("title")
            if not title:
                return None
            payload = YandexMusicReleasePayload(
                id=provider_id,
                title=title,
                artists=self._artist_names(item.get("artists")),
                release_type=item.get("type"),
                year=item.get("year"),
                track_count=item.get("trackCount"),
                url=f"https://music.yandex.ru/album/{provider_id}",
                raw_json=item,
            )
            return ProviderSearchHit(kind=kind, entity=map_release(payload))

        title = item.get("title")
        if not title:
            return None
        payload = YandexMusicTrackPayload(
            id=provider_id,
            title=title,
            artists=self._artist_names(item.get("artists")),
            duration_ms=item.get("durationMs"),
            release_title=(item.get("albums") or [{}])[0].get("title"),
            track_number=item.get("trackPosition", {}).get("index"),
            url=f"https://music.yandex.ru/track/{provider_id}",
            raw_json=item,
        )
        return ProviderSearchHit(kind=kind, entity=map_track(payload))

    def _artist_names(self, artists: Any) -> list[str]:
        if not isinstance(artists, list):
            return []
        names = []
        for artist in artists:
            if isinstance(artist, dict) and artist.get("name"):
                names.append(str(artist["name"]))
        return names
