from __future__ import annotations

from tests.test_support import seed_catalog


def test_get_artist_detail_returns_platforms_and_aliases(
    sqlite_database_url: str,
    migrated_sqlite_database,
    client,
    db_session,
) -> None:
    ids = seed_catalog(db_session)

    response = client.get(f"/artists/{ids['artist_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == ids["artist_id"]
    assert payload["partial"] is False
    assert payload["aliases"][0]["alias"] == "Кровосток"
    assert payload["releases"][0]["title"] == "Studio Session"
    assert payload["releases"][0]["track_count"] == 1
    assert payload["releases"][0]["available_platforms"] == ["youtube"]
    assert payload["releases"][0]["missing_platforms"] == ["yandex"]
    assert payload["releases"][0]["is_missing_yandex"] is True
    assert payload["platforms"]["youtube"]["provider_id"] == "yt-artist-1"
    assert payload["platforms"]["yandex"]["explainability"]["decision"] == "auto"


def test_get_artist_detail_returns_yandex_native_catalog_sections(
    sqlite_database_url: str,
    migrated_sqlite_database,
    client,
    db_session,
) -> None:
    ids = seed_catalog(db_session, include_yandex_catalog_sections=True)

    response = client.get(f"/artists/{ids['artist_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["yandex_catalog_sections"][0]["list_kind"] == "direct_albums"
    assert payload["yandex_catalog_sections"][0]["title"] == "Yandex direct albums"
    assert payload["yandex_catalog_sections"][0]["items"][0]["label"] == "Raw Yandex Sessions"
    assert payload["yandex_catalog_sections"][0]["items"][0]["subtitle"] == "2019 · album · 8 tracks"
    assert payload["yandex_catalog_sections"][1]["list_kind"] == "similar_artists"
    assert payload["yandex_catalog_sections"][1]["items"][0]["label"] == "Ploho"
    assert payload["yandex_catalog_sections"][1]["items"][0]["url"] == "https://music.yandex.test/artist/ya-artist-neighbor-1"


def test_get_artist_detail_returns_dedicated_missing_on_yandex_view(
    sqlite_database_url: str,
    migrated_sqlite_database,
    client,
    db_session,
) -> None:
    ids = seed_catalog(db_session, include_yandex_catalog_sections=True)

    response = client.get(f"/artists/{ids['artist_id']}")

    assert response.status_code == 200
    payload = response.json()
    view = payload["missing_on_yandex_view"]
    assert view["total_items"] == 3
    assert view["candidate_count"] == 1
    assert view["missing_count"] == 2

    items_by_title = {item["title"]: item for item in view["items"]}
    assert items_by_title["Raw Yandex Sessions"]["status"] == "catalog_candidate"
    assert items_by_title["Raw Yandex Sessions"]["yandex_candidates"][0]["provider_id"] == "ya-release-native-1"
    assert items_by_title["Raw Yandex Sessions"]["yandex_candidates"][0]["source_list_kinds"] == ["direct_albums"]
    assert items_by_title["Lost Tape"]["status"] == "missing"
    assert items_by_title["Lost Tape"]["yandex_candidates"] == []
    assert items_by_title["Studio Session"]["status"] == "missing"


def test_get_release_detail_returns_partial_when_one_platform_is_missing(
    sqlite_database_url: str,
    migrated_sqlite_database,
    client,
    db_session,
) -> None:
    ids = seed_catalog(db_session)

    response = client.get(f"/releases/{ids['release_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == ids["release_id"]
    assert payload["partial"] is True
    assert payload["missing_platforms"] == ["yandex"]
    assert payload["artists"][0]["display_name"] == "Krovostok"
    assert payload["tracks"][0]["track_number"] == 1
    assert payload["platforms"]["youtube"]["explainability"]["decision"] == "ambiguous"
    assert payload["platforms"]["yandex"] is None


def test_get_track_detail_returns_related_releases(
    sqlite_database_url: str,
    migrated_sqlite_database,
    client,
    db_session,
) -> None:
    ids = seed_catalog(db_session)

    response = client.get(f"/tracks/{ids['track_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == ids["track_id"]
    assert payload["partial"] is False
    assert payload["artists"][0]["display_name"] == "Krovostok"
    assert payload["releases"][0]["title"] == "Studio Session"
    assert payload["platforms"]["youtube"]["provider_id"] == "yt-track-1"


def test_get_entity_returns_404_when_missing(
    sqlite_database_url: str,
    migrated_sqlite_database,
    client,
) -> None:
    response = client.get("/artists/99999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
