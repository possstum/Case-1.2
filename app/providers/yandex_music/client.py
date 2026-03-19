from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlparse
from typing import Any, Optional
from urllib.request import Request, urlopen

from app.providers.yandex_music.mapper import map_artist, map_release, map_track
from app.providers.yandex_music.schemas import (
    YandexMusicAlbumWithTracksPayload,
    YandexMusicArtistPayload,
    YandexMusicArtistBriefInfoPayload,
    YandexMusicArtistDetailPayload,
    YandexMusicArtistDirectAlbumsPayload,
    YandexMusicArtistTracksPayload,
    YandexMusicCollectionItemPayload,
    YandexMusicPagerPayload,
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
    _api_root = "https://api.music.yandex.net"
    _search_url = f"{_api_root}/search"
    _search_page_size = 20

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
        items: list[ProviderSearchHit] = []
        for resolved_kind in self._resolve_kinds(kind):
            items.extend(self._search_kind(query, kind=resolved_kind, limit=limit))
        return ProviderSearchResult(query=query, items=items if limit is None else items[:limit])

    def get_artist(self, provider_id: str) -> ProviderArtist:
        return map_artist(self.get_artist_detail(provider_id).artist)

    def get_release(self, provider_id: str) -> ProviderRelease:
        payload = self._get_json(
            f"{self._api_root}/albums/{provider_id}",
            retry_with_auth_on_statuses=(401, 403),
        )
        release = self._release_payload_from_item(payload.get("result"))
        if release is None:
            raise ValueError(f"Yandex Music release {provider_id} was not found in response payload")
        return map_release(release)

    def get_track(self, provider_id: str) -> ProviderTrack:
        payload = self._get_json(
            f"{self._api_root}/tracks/{provider_id}",
            retry_with_auth_on_statuses=(401, 403),
        )
        result = payload.get("result")
        item = result[0] if isinstance(result, list) and result else None
        track = self._track_payload_from_item(item)
        if track is None:
            raise ValueError(f"Yandex Music track {provider_id} was not found in response payload")
        return map_track(track)

    def get_artist_detail(self, provider_id: str) -> YandexMusicArtistDetailPayload:
        payload = self._get_json(
            f"{self._api_root}/artists/{provider_id}",
            retry_with_auth_on_statuses=(401, 403),
        )
        result = payload.get("result") or {}
        artist = self._artist_payload_from_item(result.get("artist"))
        if artist is None:
            raise ValueError(f"Yandex Music artist {provider_id} was not found in response payload")
        return YandexMusicArtistDetailPayload(
            artist=artist,
            albums=self._release_payloads(result.get("albums")),
            also_albums=self._release_payloads(result.get("alsoAlbums")),
            popular_tracks=self._track_payloads(result.get("popularTracks")),
            similar_artists=self._artist_payloads(result.get("similarArtists")),
            last_releases=self._release_payloads(result.get("lastReleases")),
            videos=self._collection_item_payloads(result.get("videos")),
            clips=self._collection_item_payloads(result.get("clips")),
            vinyls=self._collection_item_payloads(result.get("vinyls")),
            raw_json=result,
        )

    def get_artist_brief_info(self, provider_id: str) -> YandexMusicArtistBriefInfoPayload:
        payload = self._get_json(
            f"{self._api_root}/artists/{provider_id}/brief-info",
            retry_with_auth_on_statuses=(401, 403),
        )
        result = payload.get("result") or {}
        artist = self._artist_payload_from_item(result.get("artist"))
        if artist is None:
            raise ValueError(f"Yandex Music artist {provider_id} was not found in brief-info payload")
        playlist_ids = [
            str(item)
            for item in (result.get("playlistIds") or [])
            if isinstance(item, (str, int))
        ]
        return YandexMusicArtistBriefInfoPayload(
            artist=artist,
            albums=self._release_payloads(result.get("albums")),
            also_albums=self._release_payloads(result.get("alsoAlbums")),
            popular_tracks=self._track_payloads(result.get("popularTracks")),
            similar_artists=self._artist_payloads(result.get("similarArtists")),
            last_releases=self._release_payloads(result.get("lastReleases")),
            videos=self._collection_item_payloads(result.get("videos")),
            clips=self._collection_item_payloads(result.get("clips")),
            vinyls=self._collection_item_payloads(result.get("vinyls")),
            stats=result.get("stats") if isinstance(result.get("stats"), dict) else {},
            playlist_ids=playlist_ids,
            playlists=self._collection_item_payloads(result.get("playlists")),
            links=self._collection_item_payloads(result.get("links")),
            has_trailer=result.get("hasTrailer") if isinstance(result.get("hasTrailer"), bool) else None,
            raw_json=result,
        )

    def get_artist_direct_albums(
        self,
        provider_id: str,
        *,
        page: int = 0,
        page_size: int = 20,
    ) -> YandexMusicArtistDirectAlbumsPayload:
        payload = self._get_json(
            f"{self._api_root}/artists/{provider_id}/direct-albums",
            params={"page": str(page), "page-size": str(page_size)},
            retry_with_auth_on_statuses=(401, 403),
        )
        result = payload.get("result") or {}
        return YandexMusicArtistDirectAlbumsPayload(
            artist_id=provider_id,
            pager=self._pager_payload_from_item(result.get("pager")),
            albums=self._release_payloads(result.get("albums")),
            raw_json=result,
        )

    def get_artist_tracks(
        self,
        provider_id: str,
        *,
        page: int = 0,
        page_size: int = 20,
    ) -> YandexMusicArtistTracksPayload:
        payload = self._get_json(
            f"{self._api_root}/artists/{provider_id}/tracks",
            params={"page": str(page), "page-size": str(page_size)},
            retry_with_auth_on_statuses=(401, 403),
        )
        result = payload.get("result") or {}
        return YandexMusicArtistTracksPayload(
            artist_id=provider_id,
            pager=self._pager_payload_from_item(result.get("pager")),
            tracks=self._track_payloads(result.get("tracks")),
            raw_json=result,
        )

    def get_release_with_tracks(self, provider_id: str) -> YandexMusicAlbumWithTracksPayload:
        payload = self._get_json(
            f"{self._api_root}/albums/{provider_id}/with-tracks",
            retry_with_auth_on_statuses=(401, 403),
        )
        result = payload.get("result") or {}
        release = self._release_payload_from_item(result)
        if release is None:
            raise ValueError(f"Yandex Music release {provider_id} was not found in with-tracks payload")
        volumes: list[list[YandexMusicTrackPayload]] = []
        for volume in result.get("volumes") or []:
            if not isinstance(volume, list):
                continue
            mapped_volume: list[YandexMusicTrackPayload] = []
            for item in volume:
                track = self._track_payload_from_item(item, fallback_release_title=release.title)
                if track is not None:
                    mapped_volume.append(track)
            volumes.append(mapped_volume)
        return YandexMusicAlbumWithTracksPayload(
            release=release,
            pager=self._pager_payload_from_item(result.get("pager")),
            volumes=volumes,
            raw_json=result,
        )

    def _get_json(
        self,
        url: str,
        *,
        params: Optional[dict[str, str]] = None,
        retry_with_auth_on_statuses: tuple[int, ...] = (),
    ) -> dict[str, Any]:
        full_url = f"{url}?{urlencode(params)}" if params else url
        try:
            return self._read_json(full_url)
        except HTTPError as exc:
            oauth_token = self._normalized_oauth_token()
            if exc.code not in retry_with_auth_on_statuses or oauth_token is None:
                raise
        request = Request(
            full_url,
            headers={"Authorization": f"OAuth {oauth_token}"},
        )
        return self._read_json(request)

    def _read_json(self, target: Request | str) -> dict[str, Any]:
        with urlopen(target, timeout=self.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _normalized_oauth_token(self) -> Optional[str]:
        raw_token = (self.token or "").strip()
        if not raw_token:
            return None

        lowered = raw_token.lower()
        if lowered.startswith("oauth "):
            raw_token = raw_token[6:].strip()
        elif lowered.startswith("bearer "):
            raw_token = raw_token[7:].strip()

        if not raw_token:
            return None

        extracted_token = self._extract_access_token(raw_token)
        if extracted_token is not None:
            raw_token = extracted_token

        if any(marker in raw_token for marker in ("&token_type=", "&expires_in=", "&cid=")):
            raw_token = raw_token.split("&", 1)[0].strip()

        return raw_token or None

    def _extract_access_token(self, raw_token: str) -> Optional[str]:
        if "access_token=" not in raw_token:
            return None

        candidates = [raw_token.lstrip("#?")]
        parsed_url = urlparse(raw_token)
        candidates.extend((parsed_url.query, parsed_url.fragment))
        for candidate in candidates:
            if not candidate:
                continue
            token = parse_qs(candidate).get("access_token", [None])[0]
            if token:
                return token.strip() or None
        return None

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

    def _search_kind(
        self,
        query: str,
        *,
        kind: ProviderEntityKind,
        limit: int | None,
    ) -> list[ProviderSearchHit]:
        items: list[ProviderSearchHit] = []
        page = 0

        while True:
            page_size = self._search_request_size(limit, current_size=len(items))
            params = {
                "text": query,
                "page": str(page),
                "type": self._search_type_for_kind(kind),
                "nocorrect": "false",
                "page-size": str(page_size),
            }
            payload = self._get_json(self._search_url, params=params)
            mapped_items = self._map_search_items(kind, payload)
            if not mapped_items:
                return items

            items.extend(mapped_items)
            if limit is not None and len(items) >= limit:
                return items[:limit]
            if len(mapped_items) < page_size:
                return items
            page += 1

    def _search_request_size(self, limit: int | None, *, current_size: int) -> int:
        if limit is None:
            return self._search_page_size
        remaining = max(1, limit - current_size)
        return min(remaining, self._search_page_size)

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

        if kind == ProviderEntityKind.ARTIST:
            payload = self._artist_payload_from_item(item)
            if payload is None:
                return None
            return ProviderSearchHit(kind=kind, entity=map_artist(payload))

        if kind == ProviderEntityKind.RELEASE:
            payload = self._release_payload_from_item(item)
            if payload is None:
                return None
            return ProviderSearchHit(kind=kind, entity=map_release(payload))

        payload = self._track_payload_from_item(item)
        if payload is None:
            return None
        return ProviderSearchHit(kind=kind, entity=map_track(payload))

    def _artist_payload_from_item(
        self,
        item: Any,
    ) -> YandexMusicArtistPayload | None:
        if not isinstance(item, dict):
            return None
        provider_id = self._string_id(item.get("id"))
        name = item.get("name")
        if provider_id is None or not isinstance(name, str) or not name:
            return None
        return YandexMusicArtistPayload(
            id=provider_id,
            name=name,
            aliases=self._artist_aliases(item),
            url=f"https://music.yandex.ru/artist/{provider_id}",
            raw_json=item,
        )

    def _release_payload_from_item(
        self,
        item: Any,
    ) -> YandexMusicReleasePayload | None:
        if not isinstance(item, dict):
            return None
        provider_id = self._string_id(item.get("id"))
        title = item.get("title")
        if provider_id is None or not isinstance(title, str) or not title:
            return None
        release_type = item.get("type")
        return YandexMusicReleasePayload(
            id=provider_id,
            title=title,
            artists=self._artist_names(item.get("artists")),
            release_type=release_type if isinstance(release_type, str) and release_type else None,
            year=item.get("year") if isinstance(item.get("year"), int) else None,
            track_count=item.get("trackCount") if isinstance(item.get("trackCount"), int) else None,
            url=f"https://music.yandex.ru/album/{provider_id}",
            raw_json=item,
        )

    def _track_payload_from_item(
        self,
        item: Any,
        *,
        fallback_release_title: Optional[str] = None,
    ) -> YandexMusicTrackPayload | None:
        if not isinstance(item, dict):
            return None
        provider_id = self._string_id(item.get("id"))
        title = item.get("title")
        if provider_id is None or not isinstance(title, str) or not title:
            return None

        track_position = item.get("trackPosition") if isinstance(item.get("trackPosition"), dict) else {}
        first_album = self._first_album(item.get("albums"))
        album_track_position = (
            first_album.get("trackPosition")
            if isinstance(first_album, dict) and isinstance(first_album.get("trackPosition"), dict)
            else {}
        )
        release_title = (
            first_album.get("title")
            if isinstance(first_album, dict) and isinstance(first_album.get("title"), str)
            else fallback_release_title
        )
        track_number = self._optional_int(track_position.get("index"))
        if track_number is None:
            track_number = self._optional_int(album_track_position.get("index"))
        disc_number = self._optional_int(track_position.get("volume"))
        if disc_number is None:
            disc_number = self._optional_int(album_track_position.get("volume"))

        return YandexMusicTrackPayload(
            id=provider_id,
            title=title,
            artists=self._artist_names(item.get("artists")),
            duration_ms=self._optional_int(item.get("durationMs")),
            release_title=release_title,
            disc_number=disc_number,
            track_number=track_number,
            url=f"https://music.yandex.ru/track/{provider_id}",
            raw_json=item,
        )

    def _artist_payloads(self, items: Any) -> list[YandexMusicArtistPayload]:
        if not isinstance(items, list):
            return []
        mapped: list[YandexMusicArtistPayload] = []
        for item in items:
            payload = self._artist_payload_from_item(item)
            if payload is not None:
                mapped.append(payload)
        return mapped

    def _release_payloads(self, items: Any) -> list[YandexMusicReleasePayload]:
        if not isinstance(items, list):
            return []
        mapped: list[YandexMusicReleasePayload] = []
        for item in items:
            payload = self._release_payload_from_item(item)
            if payload is not None:
                mapped.append(payload)
        return mapped

    def _track_payloads(self, items: Any) -> list[YandexMusicTrackPayload]:
        if not isinstance(items, list):
            return []
        mapped: list[YandexMusicTrackPayload] = []
        for item in items:
            payload = self._track_payload_from_item(item)
            if payload is not None:
                mapped.append(payload)
        return mapped

    def _collection_item_payloads(self, items: Any) -> list[YandexMusicCollectionItemPayload]:
        if not isinstance(items, list):
            return []
        mapped: list[YandexMusicCollectionItemPayload] = []
        for item in items:
            payload = self._collection_item_payload_from_item(item)
            if payload is not None:
                mapped.append(payload)
        return mapped

    def _collection_item_payload_from_item(
        self,
        item: Any,
    ) -> YandexMusicCollectionItemPayload | None:
        if not isinstance(item, dict):
            return None
        title = item.get("title")
        name = item.get("name")
        url = item.get("url")
        return YandexMusicCollectionItemPayload(
            id=self._string_id(item.get("id") or item.get("uid") or item.get("playlistUuid")),
            title=title if isinstance(title, str) else None,
            name=name if isinstance(name, str) else None,
            url=url if isinstance(url, str) else None,
            raw_json=item,
        )

    def _pager_payload_from_item(self, item: Any) -> YandexMusicPagerPayload | None:
        if not isinstance(item, dict):
            return None
        return YandexMusicPagerPayload(
            page=self._optional_int(item.get("page")),
            per_page=self._optional_int(item.get("perPage")),
            total=self._optional_int(item.get("total")),
        )

    def _artist_names(self, artists: Any) -> list[str]:
        if not isinstance(artists, list):
            return []
        names = []
        for artist in artists:
            if isinstance(artist, dict) and artist.get("name"):
                names.append(str(artist["name"]))
        return names

    def _artist_aliases(self, item: dict[str, Any]) -> list[str]:
        aliases: list[str] = []
        for key in ("decomposed", "dbAliases"):
            values = item.get(key)
            if not isinstance(values, list):
                continue
            for alias in values:
                if isinstance(alias, str) and alias and alias not in aliases:
                    aliases.append(alias)
        return aliases

    def _first_album(self, albums: Any) -> dict[str, Any] | None:
        if not isinstance(albums, list) or not albums:
            return None
        first_album = albums[0]
        return first_album if isinstance(first_album, dict) else None

    def _optional_int(self, value: Any) -> int | None:
        return value if isinstance(value, int) else None

    def _string_id(self, value: Any) -> str | None:
        if isinstance(value, (int, str)):
            string_value = str(value)
            return string_value or None
        return None
