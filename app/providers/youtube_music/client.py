from __future__ import annotations

import json
import re
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
    _search_url = "https://www.googleapis.com/youtube/v3/search"
    _channels_url = "https://www.googleapis.com/youtube/v3/channels"
    _playlists_url = "https://www.googleapis.com/youtube/v3/playlists"
    _videos_url = "https://www.googleapis.com/youtube/v3/videos"
    _search_page_size = 50
    _iso8601_duration_pattern = re.compile(
        r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
    )

    def __init__(self, *, token: Optional[str] = None, timeout_seconds: float = 5.0) -> None:
        self.token = token
        self.timeout_seconds = timeout_seconds

    def search(
        self,
        query: str,
        *,
        limit: int | None,
        kind: Optional[ProviderEntityKind] = None,
    ) -> ProviderSearchResult:
        if not self.token:
            return ProviderSearchResult(query=query)

        items: list[ProviderSearchHit] = []
        for resolved_kind in self._resolve_kinds(kind):
            items.extend(self._search_kind(query, kind=resolved_kind, limit=limit))
        return ProviderSearchResult(query=query, items=items if limit is None else items[:limit])

    def get_artist(self, provider_id: str) -> ProviderArtist:
        item = self._get_single_item(
            self._channels_url,
            params={"part": "snippet", "id": provider_id},
            entity_label="artist",
        )
        snippet = item.get("snippet") or {}
        name = snippet.get("title")
        if not name:
            raise ValueError(f"YouTube Music artist {provider_id} was not found in response payload")

        url = f"https://www.youtube.com/channel/{provider_id}"
        payload = YouTubeMusicArtistPayload(
            id=provider_id,
            name=name,
            aliases=[],
            url=url,
            raw_json={
                "id": provider_id,
                "name": name,
                "url": url,
            },
        )
        return map_artist(payload)

    def get_release(self, provider_id: str) -> ProviderRelease:
        item = self._get_single_item(
            self._playlists_url,
            params={"part": "snippet,contentDetails", "id": provider_id},
            entity_label="release",
        )
        snippet = item.get("snippet") or {}
        content_details = item.get("contentDetails") or {}
        title = snippet.get("title")
        if not title:
            raise ValueError(f"YouTube Music release {provider_id} was not found in response payload")

        artist_names = [snippet.get("channelTitle", "")] if snippet.get("channelTitle") else []
        year = self._extract_year(snippet.get("publishedAt"))
        track_count = self._optional_int(content_details.get("itemCount"))
        url = f"https://www.youtube.com/playlist?list={provider_id}"
        payload = YouTubeMusicReleasePayload(
            id=provider_id,
            title=title,
            artists=artist_names,
            year=year,
            track_count=track_count,
            url=url,
            raw_json={
                "id": provider_id,
                "title": title,
                "artist_names": artist_names,
                "track_count": track_count,
                "release_year": year,
                "url": url,
            },
        )
        return map_release(payload)

    def get_track(self, provider_id: str) -> ProviderTrack:
        item = self._get_single_item(
            self._videos_url,
            params={"part": "snippet,contentDetails", "id": provider_id},
            entity_label="track",
        )
        snippet = item.get("snippet") or {}
        content_details = item.get("contentDetails") or {}
        title = snippet.get("title")
        if not title:
            raise ValueError(f"YouTube Music track {provider_id} was not found in response payload")

        artist_names = [snippet.get("channelTitle", "")] if snippet.get("channelTitle") else []
        duration_ms = self._parse_duration_ms(content_details.get("duration"))
        url = f"https://music.youtube.com/watch?v={provider_id}"
        payload = YouTubeMusicTrackPayload(
            id=provider_id,
            title=title,
            artists=artist_names,
            duration_ms=duration_ms,
            url=url,
            raw_json={
                "id": provider_id,
                "title": title,
                "artist_names": artist_names,
                "duration_ms": duration_ms,
                "release_title": None,
                "track_number": None,
                "url": url,
            },
        )
        return map_track(payload)

    def _get_single_item(
        self,
        url: str,
        *,
        params: dict[str, str],
        entity_label: str,
    ) -> dict[str, Any]:
        payload = self._get_json(url, params=params)
        items = payload.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError(f"YouTube Music {entity_label} {params.get('id', '')} was not found in response payload")
        item = items[0]
        if not isinstance(item, dict):
            raise ValueError(f"YouTube Music {entity_label} {params.get('id', '')} was not found in response payload")
        return item

    def _get_json(self, url: str, *, params: dict[str, str]) -> dict[str, Any]:
        token = self._require_token()
        request_params = dict(params)
        request_params["key"] = token
        with urlopen(f"{url}?{urlencode(request_params)}", timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _require_token(self) -> str:
        if self.token:
            return self.token
        raise ValueError("YouTube Music token is not configured")

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

    def _search_kind(
        self,
        query: str,
        *,
        kind: ProviderEntityKind,
        limit: int | None,
    ) -> list[ProviderSearchHit]:
        items: list[ProviderSearchHit] = []
        next_page_token: str | None = None
        seen_page_tokens: set[str] = set()

        while True:
            params = {
                "part": "snippet",
                "q": query,
                "maxResults": str(self._search_request_size(limit, current_size=len(items))),
                "type": self._search_type_for_kind(kind),
            }
            if next_page_token:
                params["pageToken"] = next_page_token
            payload = self._get_json(self._search_url, params=params)
            raw_items = payload.get("items", [])
            for raw_item in raw_items:
                mapped = self._map_search_item(kind, raw_item)
                if mapped is not None:
                    items.append(mapped)
                    if limit is not None and len(items) >= limit:
                        return items[:limit]

            next_page_token = payload.get("nextPageToken")
            if not raw_items or not isinstance(next_page_token, str) or not next_page_token:
                return items
            if next_page_token in seen_page_tokens:
                return items
            seen_page_tokens.add(next_page_token)

    def _search_request_size(self, limit: int | None, *, current_size: int) -> int:
        if limit is None:
            return self._search_page_size
        remaining = max(1, limit - current_size)
        return min(remaining, self._search_page_size)

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

    def _optional_int(self, value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _parse_duration_ms(self, duration: Any) -> int | None:
        if not isinstance(duration, str):
            return None
        match = self._iso8601_duration_pattern.fullmatch(duration)
        if match is None:
            return None
        days = int(match.group("days") or 0)
        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        seconds = int(match.group("seconds") or 0)
        total_seconds = days * 86400 + hours * 3600 + minutes * 60 + seconds
        return total_seconds * 1000
