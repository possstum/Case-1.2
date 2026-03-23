from __future__ import annotations

from app.db.models import PlatformCatalogList, SyncJob
from app.db.session import get_session_factory
from app.demo.data import DEFAULT_DEMO_IDENTIFIERS, seed_demo_catalog
from app.demo.seed import main as seed_main
from tests.conftest import reset_runtime_caches


def test_seed_demo_catalog_uses_fixed_ids_and_finished_job(db_session) -> None:
    state = seed_demo_catalog(
        db_session,
        identifiers=DEFAULT_DEMO_IDENTIFIERS,
        include_yandex_catalog_sections=True,
        include_finished_job=True,
    )

    assert state.artist_id == DEFAULT_DEMO_IDENTIFIERS.artist_id
    assert state.release_id == DEFAULT_DEMO_IDENTIFIERS.release_id
    assert state.track_id == DEFAULT_DEMO_IDENTIFIERS.track_id
    assert state.job_id == DEFAULT_DEMO_IDENTIFIERS.job_id
    assert state.rq_job_id == DEFAULT_DEMO_IDENTIFIERS.rq_job_id
    assert state.candidate_release_id > 0
    assert state.missing_release_id > 0

    seeded_job = db_session.get(SyncJob, DEFAULT_DEMO_IDENTIFIERS.job_id)
    assert seeded_job is not None
    assert seeded_job.status == "finished"
    assert seeded_job.rq_job_id == DEFAULT_DEMO_IDENTIFIERS.rq_job_id
    assert seeded_job.result_json == {
        "kind": "artist",
        "target_id": str(DEFAULT_DEMO_IDENTIFIERS.artist_id),
        "updated_count": 2,
        "partial": False,
        "providers": [
            {
                "provider": "youtube",
                "provider_id": f"demo-yt-artist-{DEFAULT_DEMO_IDENTIFIERS.artist_id}",
                "status": "updated",
                "mode": "entity_refresh",
                "attempts": 1,
            },
            {
                "provider": "yandex",
                "provider_id": f"demo-ya-artist-{DEFAULT_DEMO_IDENTIFIERS.artist_id}",
                "status": "updated",
                "mode": "catalog_ingest",
                "catalog_list_count": 2,
                "attempts": 1,
            },
        ],
        "seeded": True,
    }

    catalog_lists = db_session.query(PlatformCatalogList).all()
    assert {row.list_kind for row in catalog_lists} == {"direct_albums", "similar_artists"}


def test_seeded_detail_and_job_pages_resolve(client, db_session) -> None:
    seed_demo_catalog(
        db_session,
        identifiers=DEFAULT_DEMO_IDENTIFIERS,
        include_yandex_catalog_sections=True,
        include_finished_job=True,
    )

    artist_response = client.get(f"/artists/{DEFAULT_DEMO_IDENTIFIERS.artist_id}")
    release_response = client.get(f"/releases/{DEFAULT_DEMO_IDENTIFIERS.release_id}")
    track_response = client.get(f"/tracks/{DEFAULT_DEMO_IDENTIFIERS.track_id}")
    job_response = client.get(f"/jobs/{DEFAULT_DEMO_IDENTIFIERS.job_id}")
    artist_page = client.get(f"/ui/artists/{DEFAULT_DEMO_IDENTIFIERS.artist_id}")
    job_page = client.get(f"/ui/jobs/{DEFAULT_DEMO_IDENTIFIERS.job_id}")

    assert artist_response.status_code == 200
    assert release_response.status_code == 200
    assert track_response.status_code == 200
    assert job_response.status_code == 200
    assert artist_page.status_code == 200
    assert job_page.status_code == 200
    assert artist_response.json()["yandex_catalog_sections"]
    assert artist_response.json()["missing_on_yandex_view"]["total_items"] == 3
    assert "Что есть в каталоге Yandex" in artist_page.text
    assert "Нет на Yandex" in artist_page.text
    assert "Biography" in artist_page.text
    assert "Карточка обновлена." in job_page.text


def test_seed_main_prints_ids_without_tokens(
    sqlite_database_url: str,
    migrated_sqlite_database,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setenv("DATABASE_URL", sqlite_database_url)
    monkeypatch.setenv("YOUTUBE_MUSIC_TOKEN", "secret-youtube-token")
    monkeypatch.setenv("YANDEX_MUSIC_TOKEN", "secret-yandex-token")
    reset_runtime_caches()

    assert seed_main([]) == 0

    captured = capsys.readouterr()
    assert "secret-youtube-token" not in captured.out
    assert "secret-yandex-token" not in captured.out
    assert str(DEFAULT_DEMO_IDENTIFIERS.artist_id) in captured.out
    assert DEFAULT_DEMO_IDENTIFIERS.job_id in captured.out

    session = get_session_factory()()
    try:
        seeded_job = session.get(SyncJob, DEFAULT_DEMO_IDENTIFIERS.job_id)
        assert seeded_job is not None
    finally:
        session.close()
        reset_runtime_caches()
