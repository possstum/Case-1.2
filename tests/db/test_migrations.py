from __future__ import annotations

from sqlalchemy import create_engine, inspect


def test_migration_creates_expected_tables(sqlite_database_url: str, migrated_sqlite_database) -> None:
    engine = create_engine(sqlite_database_url)
    inspector = inspect(engine)

    expected_tables = {
        "artists",
        "artist_aliases",
        "releases",
        "tracks",
        "release_artists",
        "track_artists",
        "release_tracks",
        "platform_artists",
        "platform_catalog_list_items",
        "platform_catalog_lists",
        "platform_releases",
        "platform_release_artists",
        "platform_tracks",
        "platform_track_artists",
        "platform_release_tracks",
        "links_artist",
        "links_release",
        "links_track",
        "search_cache",
        "sync_jobs",
    }

    assert expected_tables.issubset(set(inspector.get_table_names()))

    link_columns = {column["name"] for column in inspector.get_columns("links_release")}
    assert {"decision", "score", "features_json"} <= link_columns

    cache_columns = {column["name"] for column in inspector.get_columns("search_cache")}
    assert {"cache_key", "normalized_query", "response_json", "is_partial"} <= cache_columns

    sync_job_columns = {column["name"] for column in inspector.get_columns("sync_jobs")}
    assert {"status", "rq_job_id", "error_json", "attempts"} <= sync_job_columns

    platform_release_columns = {column["name"] for column in inspector.get_columns("platform_releases")}
    assert {"release_type_source", "release_type_confidence"} <= platform_release_columns

    list_columns = {column["name"] for column in inspector.get_columns("platform_catalog_lists")}
    assert {"owner_kind", "owner_platform_id", "list_kind", "source_endpoint"} <= list_columns

    list_item_columns = {column["name"] for column in inspector.get_columns("platform_catalog_list_items")}
    assert {"catalog_list_id", "item_kind", "external_ref"} <= list_item_columns

    unique_constraints = inspector.get_unique_constraints("search_cache")
    assert any(constraint["column_names"] == ["cache_key"] for constraint in unique_constraints)

    release_artist_constraints = inspector.get_unique_constraints("platform_release_artists")
    assert any(
        constraint["column_names"] == ["platform_release_id", "platform_artist_id", "role", "position"]
        for constraint in release_artist_constraints
    )

    catalog_list_constraints = inspector.get_unique_constraints("platform_catalog_lists")
    assert any(
        constraint["column_names"]
        == ["platform", "owner_kind", "owner_platform_id", "list_kind", "source_endpoint", "page"]
        for constraint in catalog_list_constraints
    )
