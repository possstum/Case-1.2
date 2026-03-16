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
        "platform_releases",
        "platform_tracks",
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

    unique_constraints = inspector.get_unique_constraints("search_cache")
    assert any(constraint["column_names"] == ["cache_key"] for constraint in unique_constraints)
