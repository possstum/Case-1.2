from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import (
    Artist,
    ArtistAlias,
    LinkArtist,
    LinkRelease,
    LinkTrack,
    PlatformArtist,
    PlatformCatalogList,
    PlatformCatalogListItem,
    PlatformRelease,
    PlatformTrack,
    Release,
    ReleaseArtist,
    ReleaseTrack,
    SyncJob,
    Track,
    TrackArtist,
)
from app.utils.normalization import display_norm, match_norm


@dataclass(frozen=True)
class DemoSeedIdentifiers:
    artist_id: int | None = None
    release_id: int | None = None
    track_id: int | None = None
    job_id: str | None = None
    rq_job_id: str | None = None


@dataclass(frozen=True)
class SeededDemoState:
    artist_id: int
    release_id: int
    track_id: int
    candidate_release_id: int = 0
    missing_release_id: int = 0
    job_id: str | None = None
    rq_job_id: str | None = None


DEFAULT_DEMO_IDENTIFIERS = DemoSeedIdentifiers(
    artist_id=910001,
    release_id=920001,
    track_id=930001,
    job_id="00000000-0000-4000-8000-000000910001",
    rq_job_id="demo-rq-910001",
)

_SEEDED_JOB_TIMESTAMP = datetime(2026, 3, 20, 12, 0, tzinfo=timezone.utc)


def seed_demo_catalog(
    session: Session,
    *,
    identifiers: DemoSeedIdentifiers | None = None,
    include_yandex_catalog_sections: bool = False,
    include_finished_job: bool = False,
) -> SeededDemoState:
    ids = identifiers or DemoSeedIdentifiers()
    use_runtime_demo_provider_ids = ids.artist_id is not None or ids.release_id is not None or ids.track_id is not None
    provider_values = _provider_seed_values(
        artist_id=ids.artist_id,
        release_id=ids.release_id,
        track_id=ids.track_id,
        use_runtime_demo_provider_ids=use_runtime_demo_provider_ids,
    )

    artist = Artist(
        id=ids.artist_id,
        display_name="Krovostok",
        display_norm=display_norm("Krovostok"),
        match_norm=match_norm("Krovostok"),
        metadata_json={"seeded": True, "source": "demo"},
    )
    release = Release(
        id=ids.release_id,
        title="Studio Session",
        display_norm=display_norm("Studio Session"),
        match_norm=match_norm("Studio Session"),
        release_type="album",
        release_year=2024,
        metadata_json={"seeded": True, "source": "demo"},
    )
    track = Track(
        id=ids.track_id,
        title="Biography",
        display_norm=display_norm("Biography"),
        match_norm=match_norm("Biography"),
        duration_ms=185000,
        metadata_json={"seeded": True, "source": "demo"},
    )
    session.add_all([artist, release, track])
    session.flush()

    session.add(
        ArtistAlias(
            artist_id=artist.id,
            alias="Кровосток",
            display_norm=display_norm("Кровосток"),
            match_norm=match_norm("Кровосток"),
            source="seed",
        )
    )
    session.add_all(
        [
            ReleaseArtist(release_id=release.id, artist_id=artist.id, role="primary", position=0),
            TrackArtist(track_id=track.id, artist_id=artist.id, role="primary", position=0),
            ReleaseTrack(
                release_id=release.id,
                track_id=track.id,
                position=1,
                disc_number=1,
                track_number=1,
            ),
        ]
    )

    platform_artist_youtube = PlatformArtist(
        platform="youtube",
        platform_id=provider_values["artist_youtube_id"],
        display_name="Кровосток",
        display_norm=display_norm("Кровосток"),
        match_norm=match_norm("Кровосток"),
        raw_json={"url": provider_values["artist_youtube_url"], "seeded": True},
    )
    platform_artist_yandex = PlatformArtist(
        platform="yandex",
        platform_id=provider_values["artist_yandex_id"],
        display_name="Krovostok",
        display_norm=display_norm("Krovostok"),
        match_norm=match_norm("Krovostok"),
        raw_json={"url": provider_values["artist_yandex_url"], "seeded": True},
    )
    platform_release_youtube = PlatformRelease(
        platform="youtube",
        platform_id=provider_values["release_youtube_id"],
        title=release.title,
        display_norm=release.display_norm,
        match_norm=release.match_norm,
        release_type=release.release_type,
        release_year=release.release_year,
        raw_json={
            "artist_names": [artist.display_name],
            "track_count": 1,
            "url": provider_values["release_youtube_url"],
            "seeded": True,
        },
    )
    platform_track_youtube = PlatformTrack(
        platform="youtube",
        platform_id=provider_values["track_youtube_id"],
        title=track.title,
        display_norm=track.display_norm,
        match_norm=track.match_norm,
        duration_ms=track.duration_ms,
        raw_json={
            "artist_names": [artist.display_name],
            "url": provider_values["track_youtube_url"],
            "seeded": True,
        },
    )
    platform_track_yandex = PlatformTrack(
        platform="yandex",
        platform_id=provider_values["track_yandex_id"],
        title=track.title,
        display_norm=track.display_norm,
        match_norm=track.match_norm,
        duration_ms=track.duration_ms,
        raw_json={
            "artist_names": [artist.display_name],
            "url": provider_values["track_yandex_url"],
            "seeded": True,
        },
    )
    session.add_all(
        [
            platform_artist_youtube,
            platform_artist_yandex,
            platform_release_youtube,
            platform_track_youtube,
            platform_track_yandex,
        ]
    )
    session.flush()

    candidate_release_id = 0
    missing_release_id = 0

    if include_yandex_catalog_sections:
        (
            candidate_release_id,
            missing_release_id,
        ) = _seed_yandex_catalog_sections(
            session=session,
            artist=artist,
            platform_artist_yandex=platform_artist_yandex,
            use_runtime_demo_provider_ids=use_runtime_demo_provider_ids,
        )

    session.add_all(
        [
            LinkArtist(
                artist_id=artist.id,
                platform_artist_id=platform_artist_youtube.id,
                decision="auto",
                score=0.99,
                features_json={"name_similarity": 1.0, "seeded": True},
            ),
            LinkArtist(
                artist_id=artist.id,
                platform_artist_id=platform_artist_yandex.id,
                decision="auto",
                score=0.99,
                features_json={"name_similarity": 0.98, "seeded": True},
            ),
            LinkRelease(
                release_id=release.id,
                platform_release_id=platform_release_youtube.id,
                decision="ambiguous",
                score=0.72,
                features_json={"title_similarity": 0.9, "year_delta": 0, "seeded": True},
            ),
            LinkTrack(
                track_id=track.id,
                platform_track_id=platform_track_youtube.id,
                decision="auto",
                score=0.94,
                features_json={"duration_delta_ms": 0, "seeded": True},
            ),
            LinkTrack(
                track_id=track.id,
                platform_track_id=platform_track_yandex.id,
                decision="auto",
                score=0.94,
                features_json={"duration_delta_ms": 0, "seeded": True},
            ),
        ]
    )

    job_id = None
    rq_job_id = None
    if include_finished_job:
        job_id = ids.job_id or "00000000-0000-4000-8000-000000000001"
        rq_job_id = ids.rq_job_id or "demo-rq-job-1"
        session.add(
            SyncJob(
                id=job_id,
                kind="artist",
                target_id=str(artist.id),
                status="finished",
                queue_name="default",
                rq_job_id=rq_job_id,
                payload_json={"kind": "artist", "target_id": str(artist.id), "seeded": True},
                result_json={
                    "kind": "artist",
                    "target_id": str(artist.id),
                    "updated_count": 2,
                    "partial": False,
                    "providers": [
                        {
                            "provider": "youtube",
                            "provider_id": platform_artist_youtube.platform_id,
                            "status": "updated",
                            "mode": "entity_refresh",
                            "attempts": 1,
                        },
                        {
                            "provider": "yandex",
                            "provider_id": platform_artist_yandex.platform_id,
                            "status": "updated",
                            "mode": "catalog_ingest",
                            "catalog_list_count": 2,
                            "attempts": 1,
                        },
                    ],
                    "seeded": True,
                },
                attempts=1,
                started_at=_SEEDED_JOB_TIMESTAMP,
                finished_at=_SEEDED_JOB_TIMESTAMP,
            )
        )

    session.commit()
    return SeededDemoState(
        artist_id=artist.id,
        release_id=release.id,
        track_id=track.id,
        candidate_release_id=candidate_release_id,
        missing_release_id=missing_release_id,
        job_id=job_id,
        rq_job_id=rq_job_id,
    )


def _seed_yandex_catalog_sections(
    *,
    session: Session,
    artist: Artist,
    platform_artist_yandex: PlatformArtist,
    use_runtime_demo_provider_ids: bool,
) -> tuple[int, int]:
    platform_release_yandex_native = PlatformRelease(
        platform="yandex",
        platform_id=(
            f"demo-ya-release-native-{artist.id}"
            if use_runtime_demo_provider_ids
            else "ya-release-native-1"
        ),
        title="Raw Yandex Sessions",
        display_norm=display_norm("Raw Yandex Sessions"),
        match_norm=match_norm("Raw Yandex Sessions"),
        release_type="album",
        release_year=2019,
        raw_json={
            "artist_names": [artist.display_name],
            "track_count": 8,
            "url": (
                f"https://demo.yandex.test/release/native-{artist.id}"
                if use_runtime_demo_provider_ids
                else "https://music.yandex.test/release/ya-release-native-1"
            ),
            "seeded": True,
        },
    )
    platform_artist_yandex_neighbor = PlatformArtist(
        platform="yandex",
        platform_id=(
            f"demo-ya-artist-neighbor-{artist.id}"
            if use_runtime_demo_provider_ids
            else "ya-artist-neighbor-1"
        ),
        display_name="Ploho",
        display_norm=display_norm("Ploho"),
        match_norm=match_norm("Ploho"),
        raw_json={
            "url": (
                f"https://demo.yandex.test/artist/neighbor-{artist.id}"
                if use_runtime_demo_provider_ids
                else "https://music.yandex.test/artist/ya-artist-neighbor-1"
            ),
            "seeded": True,
        },
    )
    session.add_all([platform_release_yandex_native, platform_artist_yandex_neighbor])
    session.flush()

    direct_albums_list = PlatformCatalogList(
        platform="yandex",
        owner_kind="artist",
        owner_platform_id=platform_artist_yandex.platform_id,
        list_kind="direct_albums",
        source_endpoint=f"/artists/{platform_artist_yandex.platform_id}/direct-albums",
        title="Direct albums",
        page=0,
        page_size=1,
        total_items=1,
        raw_json={"seeded": True},
    )
    similar_artists_list = PlatformCatalogList(
        platform="yandex",
        owner_kind="artist",
        owner_platform_id=platform_artist_yandex.platform_id,
        list_kind="similar_artists",
        source_endpoint=f"/artists/{platform_artist_yandex.platform_id}",
        title="Similar artists",
        page=0,
        page_size=1,
        total_items=1,
        raw_json={"seeded": True},
    )
    session.add_all([direct_albums_list, similar_artists_list])
    session.flush()
    session.add_all(
        [
            PlatformCatalogListItem(
                catalog_list_id=direct_albums_list.id,
                position=0,
                item_kind="release",
                platform_release_id=platform_release_yandex_native.id,
                raw_json={"title": platform_release_yandex_native.title, "seeded": True},
            ),
            PlatformCatalogListItem(
                catalog_list_id=similar_artists_list.id,
                position=0,
                item_kind="artist",
                platform_artist_id=platform_artist_yandex_neighbor.id,
                raw_json={"title": platform_artist_yandex_neighbor.display_name, "seeded": True},
            ),
        ]
    )

    candidate_release = Release(
        title="Raw Yandex Sessions",
        display_norm=display_norm("Raw Yandex Sessions"),
        match_norm=match_norm("Raw Yandex Sessions"),
        release_type="album",
        release_year=2019,
        metadata_json={"seeded": True, "source": "demo"},
    )
    missing_release = Release(
        title="Lost Tape",
        display_norm=display_norm("Lost Tape"),
        match_norm=match_norm("Lost Tape"),
        release_type="ep",
        release_year=2018,
        metadata_json={"seeded": True, "source": "demo"},
    )
    session.add_all([candidate_release, missing_release])
    session.flush()
    session.add_all(
        [
            ReleaseArtist(release_id=candidate_release.id, artist_id=artist.id, role="primary", position=1),
            ReleaseArtist(release_id=missing_release.id, artist_id=artist.id, role="primary", position=2),
        ]
    )

    platform_release_youtube_candidate = PlatformRelease(
        platform="youtube",
        platform_id=(
            f"demo-yt-release-candidate-{artist.id}"
            if use_runtime_demo_provider_ids
            else "yt-release-2"
        ),
        title="Raw Yandex Sessions",
        display_norm=display_norm("Raw Yandex Sessions"),
        match_norm=match_norm("Raw Yandex Sessions"),
        release_type="album",
        release_year=2019,
        raw_json={
            "artist_names": [artist.display_name],
            "track_count": 8,
            "url": (
                f"https://demo.youtube.test/release/candidate-{artist.id}"
                if use_runtime_demo_provider_ids
                else "https://music.youtube.test/release/yt-release-2"
            ),
            "seeded": True,
        },
    )
    platform_release_youtube_missing = PlatformRelease(
        platform="youtube",
        platform_id=(
            f"demo-yt-release-missing-{artist.id}"
            if use_runtime_demo_provider_ids
            else "yt-release-3"
        ),
        title="Lost Tape",
        display_norm=display_norm("Lost Tape"),
        match_norm=match_norm("Lost Tape"),
        release_type="ep",
        release_year=2018,
        raw_json={
            "artist_names": [artist.display_name],
            "track_count": 5,
            "url": (
                f"https://demo.youtube.test/release/missing-{artist.id}"
                if use_runtime_demo_provider_ids
                else "https://music.youtube.test/release/yt-release-3"
            ),
            "seeded": True,
        },
    )
    session.add_all([platform_release_youtube_candidate, platform_release_youtube_missing])
    session.flush()
    session.add_all(
        [
            LinkRelease(
                release_id=candidate_release.id,
                platform_release_id=platform_release_youtube_candidate.id,
                decision="auto",
                score=0.93,
                features_json={"title_similarity": 1.0, "year_delta": 0, "seeded": True},
            ),
            LinkRelease(
                release_id=missing_release.id,
                platform_release_id=platform_release_youtube_missing.id,
                decision="auto",
                score=0.92,
                features_json={"title_similarity": 1.0, "year_delta": 0, "seeded": True},
            ),
        ]
    )
    return candidate_release.id, missing_release.id


def _provider_seed_values(
    *,
    artist_id: int | None,
    release_id: int | None,
    track_id: int | None,
    use_runtime_demo_provider_ids: bool,
) -> dict[str, str]:
    if use_runtime_demo_provider_ids:
        return {
            "artist_youtube_id": f"demo-yt-artist-{artist_id}",
            "artist_youtube_url": f"https://demo.youtube.test/artist/{artist_id}",
            "artist_yandex_id": f"demo-ya-artist-{artist_id}",
            "artist_yandex_url": f"https://demo.yandex.test/artist/{artist_id}",
            "release_youtube_id": f"demo-yt-release-{release_id}",
            "release_youtube_url": f"https://demo.youtube.test/release/{release_id}",
            "track_youtube_id": f"demo-yt-track-{track_id}",
            "track_youtube_url": f"https://demo.youtube.test/track/{track_id}",
            "track_yandex_id": f"demo-ya-track-{track_id}",
            "track_yandex_url": f"https://demo.yandex.test/track/{track_id}",
        }
    return {
        "artist_youtube_id": "yt-artist-1",
        "artist_youtube_url": "https://music.youtube.test/artist/yt-artist-1",
        "artist_yandex_id": "ya-artist-1",
        "artist_yandex_url": "https://music.yandex.test/artist/ya-artist-1",
        "release_youtube_id": "yt-release-1",
        "release_youtube_url": "https://music.youtube.test/release/yt-release-1",
        "track_youtube_id": "yt-track-1",
        "track_youtube_url": "https://music.youtube.test/track/yt-track-1",
        "track_yandex_id": "ya-track-1",
        "track_yandex_url": "https://music.yandex.test/track/ya-track-1",
    }
