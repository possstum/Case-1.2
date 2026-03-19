from __future__ import annotations

from typing import Optional

from fastapi.testclient import TestClient

from app.api.deps import (
    get_health_service,
    get_optional_provider_registry,
    get_provider_registry,
    get_search_rate_limiter,
    get_sync_rate_limiter,
    get_sync_job_scheduler,
)
from app.db.models import (
    LinkArtist,
    LinkRelease,
    LinkTrack,
    PlatformArtist,
    PlatformCatalogList,
    PlatformCatalogListItem,
    PlatformRelease,
    PlatformTrack,
)
from app.db.repositories.artists import ArtistRepository
from app.db.repositories.releases import ReleaseRepository
from app.db.repositories.tracks import TrackRepository
from app.main import create_app
from app.providers import (
    MusicProvider,
    ProviderArtist,
    ProviderEntityKind,
    ProviderName,
    ProviderRegistry,
    ProviderRelease,
    ProviderSearchHit,
    ProviderSearchResult,
    ProviderTrack,
)
from app.utils.normalization import display_norm, match_norm
from tests.conftest import StubHealthService


def make_artist(provider: ProviderName, provider_id: str, name: str, *, url: Optional[str] = None) -> ProviderArtist:
    return ProviderArtist(
        provider=provider,
        provider_id=provider_id,
        name=name,
        display_norm=display_norm(name),
        match_norm=match_norm(name),
        raw_json={"url": url} if url else {},
        url=url,
    )


def make_release(
    provider: ProviderName,
    provider_id: str,
    title: str,
    *,
    artist_names: Optional[list[str]] = None,
    release_year: Optional[int] = None,
    url: Optional[str] = None,
) -> ProviderRelease:
    return ProviderRelease(
        provider=provider,
        provider_id=provider_id,
        title=title,
        display_norm=display_norm(title),
        match_norm=match_norm(title),
        artist_names=artist_names or [],
        artist_match_norms=[match_norm(name) for name in artist_names or []],
        release_year=release_year,
        raw_json={
            "artist_names": artist_names or [],
            "track_count": 1,
            "url": url,
        },
        url=url,
    )


def make_track(
    provider: ProviderName,
    provider_id: str,
    title: str,
    *,
    artist_names: Optional[list[str]] = None,
    duration_ms: Optional[int] = None,
    url: Optional[str] = None,
) -> ProviderTrack:
    return ProviderTrack(
        provider=provider,
        provider_id=provider_id,
        title=title,
        display_norm=display_norm(title),
        match_norm=match_norm(title),
        artist_names=artist_names or [],
        artist_match_norms=[match_norm(name) for name in artist_names or []],
        duration_ms=duration_ms,
        raw_json={"artist_names": artist_names or [], "url": url},
        url=url,
    )


class StubProvider(MusicProvider):
    def __init__(
        self,
        *,
        provider_name: ProviderName,
        search_hits: Optional[list[ProviderSearchHit]] = None,
        artists: Optional[dict[str, ProviderArtist]] = None,
        releases: Optional[dict[str, ProviderRelease]] = None,
        tracks: Optional[dict[str, ProviderTrack]] = None,
        search_error: Exception | None = None,
        get_error: Exception | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.search_hits = search_hits or []
        self.artists = artists or {}
        self.releases = releases or {}
        self.tracks = tracks or {}
        self.search_error = search_error
        self.get_error = get_error

    def search(
        self,
        query: str,
        *,
        limit: int | None,
        kind: Optional[ProviderEntityKind] = None,
    ) -> ProviderSearchResult:
        if self.search_error is not None:
            raise self.search_error
        items = self.search_hits
        if kind is not None:
            items = [item for item in items if item.kind == kind]
        return ProviderSearchResult(query=query, items=items if limit is None else items[:limit])

    def get_artist(self, provider_id: str) -> ProviderArtist:
        if self.get_error is not None:
            raise self.get_error
        return self.artists[provider_id]

    def get_release(self, provider_id: str) -> ProviderRelease:
        if self.get_error is not None:
            raise self.get_error
        return self.releases[provider_id]

    def get_track(self, provider_id: str) -> ProviderTrack:
        if self.get_error is not None:
            raise self.get_error
        return self.tracks[provider_id]


class AllowAllLimiter:
    def allow(self, **_: object) -> bool:
        return True


class DenyAllLimiter:
    def allow(self, **_: object) -> bool:
        return False


class RecordingSyncScheduler:
    def __init__(self, rq_job_id: str = "rq-job-1") -> None:
        self.rq_job_id = rq_job_id
        self.calls: list[dict[str, str]] = []

    def schedule(self, *, job_id: str, queue_name: str) -> Optional[str]:
        self.calls.append({"job_id": job_id, "queue_name": queue_name})
        return self.rq_job_id


def create_test_client(
    *,
    provider_registry: Optional[ProviderRegistry] = None,
    limiter: Optional[AllowAllLimiter] = None,
    sync_scheduler: Optional[RecordingSyncScheduler] = None,
) -> TestClient:
    application = create_app()
    application.dependency_overrides[get_health_service] = lambda: StubHealthService()
    if provider_registry is not None:
        application.dependency_overrides[get_optional_provider_registry] = lambda: provider_registry
        application.dependency_overrides[get_provider_registry] = lambda: provider_registry
    if limiter is not None:
        application.dependency_overrides[get_search_rate_limiter] = lambda: limiter
        application.dependency_overrides[get_sync_rate_limiter] = lambda: limiter
    if sync_scheduler is not None:
        application.dependency_overrides[get_sync_job_scheduler] = lambda: sync_scheduler
    return TestClient(application)


def seed_catalog(session, *, include_yandex_catalog_sections: bool = False) -> dict[str, int]:
    artist_repository = ArtistRepository(session)
    release_repository = ReleaseRepository(session)
    track_repository = TrackRepository(session)

    artist = artist_repository.create(
        display_name="Krovostok",
        display_norm=display_norm("Krovostok"),
        match_norm=match_norm("Krovostok"),
        aliases=[
            {
                "alias": "Кровосток",
                "display_norm": display_norm("Кровосток"),
                "match_norm": match_norm("Кровосток"),
                "source": "seed",
            }
        ],
    )
    release = release_repository.create(
        title="Studio Session",
        display_norm=display_norm("Studio Session"),
        match_norm=match_norm("Studio Session"),
        release_type="album",
        release_year=2024,
    )
    track = track_repository.create(
        title="Biography",
        display_norm=display_norm("Biography"),
        match_norm=match_norm("Biography"),
        duration_ms=185000,
    )
    release_repository.add_artist(release=release, artist=artist)
    track_repository.add_artist(track=track, artist=artist)
    release_repository.add_track(release=release, track=track, position=1, disc_number=1, track_number=1)

    platform_artist_youtube = PlatformArtist(
        platform="youtube",
        platform_id="yt-artist-1",
        display_name="Кровосток",
        display_norm=display_norm("Кровосток"),
        match_norm=match_norm("Кровосток"),
        raw_json={"url": "https://music.youtube.test/artist/yt-artist-1"},
    )
    platform_artist_yandex = PlatformArtist(
        platform="yandex",
        platform_id="ya-artist-1",
        display_name="Krovostok",
        display_norm=display_norm("Krovostok"),
        match_norm=match_norm("Krovostok"),
        raw_json={"url": "https://music.yandex.test/artist/ya-artist-1"},
    )
    platform_release_youtube = PlatformRelease(
        platform="youtube",
        platform_id="yt-release-1",
        title="Studio Session",
        display_norm=display_norm("Studio Session"),
        match_norm=match_norm("Studio Session"),
        release_type="album",
        release_year=2024,
        raw_json={
            "artist_names": ["Krovostok"],
            "track_count": 1,
            "url": "https://music.youtube.test/release/yt-release-1",
        },
    )
    platform_track_youtube = PlatformTrack(
        platform="youtube",
        platform_id="yt-track-1",
        title="Biography",
        display_norm=display_norm("Biography"),
        match_norm=match_norm("Biography"),
        duration_ms=185000,
        raw_json={
            "artist_names": ["Krovostok"],
            "url": "https://music.youtube.test/track/yt-track-1",
        },
    )
    platform_track_yandex = PlatformTrack(
        platform="yandex",
        platform_id="ya-track-1",
        title="Biography",
        display_norm=display_norm("Biography"),
        match_norm=match_norm("Biography"),
        duration_ms=185000,
        raw_json={
            "artist_names": ["Krovostok"],
            "url": "https://music.yandex.test/track/ya-track-1",
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
    candidate_release = None
    missing_release = None

    if include_yandex_catalog_sections:
        platform_release_yandex_native = PlatformRelease(
            platform="yandex",
            platform_id="ya-release-native-1",
            title="Raw Yandex Sessions",
            display_norm=display_norm("Raw Yandex Sessions"),
            match_norm=match_norm("Raw Yandex Sessions"),
            release_type="album",
            release_year=2019,
            raw_json={
                "artist_names": ["Krovostok"],
                "track_count": 8,
                "url": "https://music.yandex.test/release/ya-release-native-1",
            },
        )
        platform_artist_yandex_neighbor = PlatformArtist(
            platform="yandex",
            platform_id="ya-artist-neighbor-1",
            display_name="Ploho",
            display_norm=display_norm("Ploho"),
            match_norm=match_norm("Ploho"),
            raw_json={"url": "https://music.yandex.test/artist/ya-artist-neighbor-1"},
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
            raw_json={},
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
            raw_json={},
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
                    raw_json={"title": platform_release_yandex_native.title},
                ),
                PlatformCatalogListItem(
                    catalog_list_id=similar_artists_list.id,
                    position=0,
                    item_kind="artist",
                    platform_artist_id=platform_artist_yandex_neighbor.id,
                    raw_json={"title": platform_artist_yandex_neighbor.display_name},
                ),
            ]
        )

        candidate_release = release_repository.create(
            title="Raw Yandex Sessions",
            display_norm=display_norm("Raw Yandex Sessions"),
            match_norm=match_norm("Raw Yandex Sessions"),
            release_type="album",
            release_year=2019,
        )
        missing_release = release_repository.create(
            title="Lost Tape",
            display_norm=display_norm("Lost Tape"),
            match_norm=match_norm("Lost Tape"),
            release_type="ep",
            release_year=2018,
        )
        release_repository.add_artist(release=candidate_release, artist=artist, position=1)
        release_repository.add_artist(release=missing_release, artist=artist, position=2)

        platform_release_youtube_candidate = PlatformRelease(
            platform="youtube",
            platform_id="yt-release-2",
            title="Raw Yandex Sessions",
            display_norm=display_norm("Raw Yandex Sessions"),
            match_norm=match_norm("Raw Yandex Sessions"),
            release_type="album",
            release_year=2019,
            raw_json={
                "artist_names": ["Krovostok"],
                "track_count": 8,
                "url": "https://music.youtube.test/release/yt-release-2",
            },
        )
        platform_release_youtube_missing = PlatformRelease(
            platform="youtube",
            platform_id="yt-release-3",
            title="Lost Tape",
            display_norm=display_norm("Lost Tape"),
            match_norm=match_norm("Lost Tape"),
            release_type="ep",
            release_year=2018,
            raw_json={
                "artist_names": ["Krovostok"],
                "track_count": 5,
                "url": "https://music.youtube.test/release/yt-release-3",
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
                    features_json={"title_similarity": 1.0, "year_delta": 0},
                ),
                LinkRelease(
                    release_id=missing_release.id,
                    platform_release_id=platform_release_youtube_missing.id,
                    decision="auto",
                    score=0.92,
                    features_json={"title_similarity": 1.0, "year_delta": 0},
                ),
            ]
        )

    session.add_all(
        [
            LinkArtist(
                artist_id=artist.id,
                platform_artist_id=platform_artist_youtube.id,
                decision="auto",
                score=0.99,
                features_json={"name_similarity": 1.0},
            ),
            LinkArtist(
                artist_id=artist.id,
                platform_artist_id=platform_artist_yandex.id,
                decision="auto",
                score=0.99,
                features_json={"name_similarity": 0.98},
            ),
            LinkRelease(
                release_id=release.id,
                platform_release_id=platform_release_youtube.id,
                decision="ambiguous",
                score=0.72,
                features_json={"title_similarity": 0.9, "year_delta": 0},
            ),
            LinkTrack(
                track_id=track.id,
                platform_track_id=platform_track_youtube.id,
                decision="auto",
                score=0.94,
                features_json={"duration_delta_ms": 0},
            ),
            LinkTrack(
                track_id=track.id,
                platform_track_id=platform_track_yandex.id,
                decision="auto",
                score=0.94,
                features_json={"duration_delta_ms": 0},
            ),
        ]
    )
    session.commit()
    return {
        "artist_id": artist.id,
        "release_id": release.id,
        "track_id": track.id,
        "candidate_release_id": candidate_release.id if include_yandex_catalog_sections else 0,
        "missing_release_id": missing_release.id if include_yandex_catalog_sections else 0,
    }
