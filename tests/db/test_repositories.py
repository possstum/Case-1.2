from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.repositories import (
    ArtistRepository,
    ReleaseRepository,
    SearchCacheRepository,
    SyncJobRepository,
    TrackRepository,
)


def test_artist_repository_persists_artist_and_aliases(db_session) -> None:
    repository = ArtistRepository(db_session)

    artist = repository.create(
        display_name="Krovostok",
        display_norm="krovostok",
        match_norm="krovostok",
        aliases=[
            {
                "alias": "Кровосток",
                "display_norm": "кровосток",
                "match_norm": "krovostok",
                "source": "seed",
            }
        ],
    )
    db_session.commit()
    db_session.expire_all()

    loaded = repository.get(artist.id)

    assert loaded is not None
    assert loaded.display_name == "Krovostok"
    assert len(loaded.aliases) == 1
    assert loaded.aliases[0].alias == "Кровосток"
    assert repository.get_by_match_norm("krovostok")[0].id == artist.id


def test_release_and_track_repositories_link_entities(db_session) -> None:
    artist_repository = ArtistRepository(db_session)
    release_repository = ReleaseRepository(db_session)
    track_repository = TrackRepository(db_session)

    artist = artist_repository.create(
        display_name="Shortparis",
        display_norm="shortparis",
        match_norm="shortparis",
    )
    track = track_repository.create(
        title="Говорит Москва",
        display_norm="говорит москва",
        match_norm="govorit moskva",
        duration_ms=203000,
    )
    release = release_repository.create(
        title="Так закалялась сталь",
        display_norm="так закалялась сталь",
        match_norm="tak zakalyalas stal",
        release_type="album",
        release_year=2019,
    )

    track_repository.add_artist(track=track, artist=artist, role="primary", position=0)
    release_repository.add_artist(release=release, artist=artist, role="primary", position=0)
    release_repository.add_track(release=release, track=track, position=1, disc_number=1, track_number=1)
    db_session.commit()
    db_session.expire_all()

    loaded_release = release_repository.get(release.id)
    loaded_track = track_repository.get(track.id)

    assert loaded_release is not None
    assert loaded_track is not None
    assert loaded_release.artists[0].artist.display_name == "Shortparis"
    assert loaded_release.tracks[0].track.title == "Говорит Москва"
    assert loaded_track.artists[0].artist.id == artist.id


def test_search_cache_repository_upserts_entries(db_session) -> None:
    repository = SearchCacheRepository(db_session)
    now = datetime.now(timezone.utc)

    created = repository.upsert(
        cache_key="search:artist:krovostok",
        query_text="Кровосток",
        normalized_query="krovostok",
        kind="artist",
        response_json={"results": [1]},
        is_partial=False,
        stale_at=now + timedelta(minutes=5),
        expires_at=now + timedelta(minutes=30),
    )
    repository.mark_hit(created)
    db_session.commit()

    updated = repository.upsert(
        cache_key="search:artist:krovostok",
        query_text="Кровосток",
        normalized_query="krovostok",
        kind="artist",
        response_json={"results": [1, 2]},
        is_partial=True,
        stale_at=now + timedelta(minutes=10),
        expires_at=now + timedelta(minutes=40),
    )
    db_session.commit()

    assert created.id == updated.id
    assert updated.hit_count == 1
    assert updated.is_partial is True
    assert updated.response_json["results"] == [1, 2]


def test_sync_job_repository_tracks_status_transitions(db_session) -> None:
    repository = SyncJobRepository(db_session)

    sync_job = repository.create(
        kind="release",
        target_id="42",
        queue_name="default",
        rq_job_id="rq-42",
        payload_json={"force": True},
    )
    repository.mark_started(sync_job, attempts=1)
    repository.mark_finished(sync_job, result_json={"linked": 3})
    db_session.commit()
    db_session.expire_all()

    loaded = repository.get(sync_job.id)

    assert loaded is not None
    assert loaded.status == "finished"
    assert loaded.attempts == 1
    assert loaded.result_json == {"linked": 3}
    assert loaded.rq_job_id == "rq-42"
    assert loaded.started_at is not None
    assert loaded.finished_at is not None
