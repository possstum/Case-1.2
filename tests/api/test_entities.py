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
