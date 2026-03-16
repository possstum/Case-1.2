from __future__ import annotations

import json
from typing import Any, Optional
from urllib.parse import urlencode
from urllib.request import urlopen

from app.providers.youtube_music.mapper import map_artist, map_release, map_track
from app.providers.youtube_music.schemas import (
    YouTubeMusicArtistPayload,
    YouTubeMusicReleasePayload,
    YouTubeMusicTrackPayload,
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


class YouTubeMusicClient(MusicProvider):
    provider_name = ProviderName.YOUTUBE
    _base_url = "https://www.googleapis.com/youtube/v3/search"

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
                "part": "snippet",
                "q": query,
                "maxResults": str(limit),
                "type": self._search_type_for_kind(resolved_kind),
                "key": self.token,
            }
            payload = self._get_json(self._base_url, params=params)
            for raw_item in payload.get("items", []):
                mapped = self._map_search_item(resolved_kind, raw_item)
                if mapped is not None:
                    items.append(mapped)
        return ProviderSearchResult(query=query, items=items[:limit])

    def get_artist(self, provider_id: str) -> ProviderArtist:
        raise NotImplementedError("YouTube Music provider integration is not implemented yet")

    def get_release(self, provider_id: str) -> ProviderRelease:
        raise NotImplementedError("YouTube Music provider integration is not implemented yet")

    def get_track(self, provider_id: str) -> ProviderTrack:
        raise NotImplementedError("YouTube Music provider integration is not implemented yet")

    def _get_json(self, url: str, *, params: dict[str, str]) -> dict[str, Any]:
        with urlopen(f"{url}?{urlencode(params)}", timeout=self.timeout_seconds) as response:
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
            return "channel"
        if kind == ProviderEntityKind.RELEASE:
            return "playlist"
        return "video"

    def _map_search_item(
        self,
        kind: ProviderEntityKind,
        item: dict[str, Any],
    ) -> ProviderSearchHit | None:
        item_id = item.get("id", {})
        snippet = item.get("snippet", {})
        title = snippet.get("title")
        if not title:
            return None

        if kind == ProviderEntityKind.ARTIST:
            provider_id = item_id.get("channelId")
            if not provider_id:
                return None
            payload = YouTubeMusicArtistPayload(
                id=provider_id,
                name=title,
                aliases=[],
                url=f"https://www.youtube.com/channel/{provider_id}",
                raw_json=item,
            )
            return ProviderSearchHit(kind=kind, entity=map_artist(payload))

        if kind == ProviderEntityKind.RELEASE:
            provider_id = item_id.get("playlistId")
            if not provider_id:
                return None
            payload = YouTubeMusicReleasePayload(
                id=provider_id,
                title=title,
                artists=[snippet.get("channelTitle", "")] if snippet.get("channelTitle") else [],
                year=self._extract_year(snippet.get("publishedAt")),
                url=f"https://www.youtube.com/playlist?list={provider_id}",
                raw_json=item,
            )
            return ProviderSearchHit(kind=kind, entity=map_release(payload))

        provider_id = item_id.get("videoId")
        if not provider_id:
            return None
        payload = YouTubeMusicTrackPayload(
            id=provider_id,
            title=title,
            artists=[snippet.get("channelTitle", "")] if snippet.get("channelTitle") else [],
            url=f"https://music.youtube.com/watch?v={provider_id}",
            raw_json=item,
        )
        return ProviderSearchHit(kind=kind, entity=map_track(payload))

    def _extract_year(self, published_at: Any) -> int | None:
        if not isinstance(published_at, str) or len(published_at) < 4:
            return None
        try:
            return int(published_at[:4])
        except ValueError:
            return None
