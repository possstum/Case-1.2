from __future__ import annotations

from typing import Optional

from fastapi.testclient import TestClient

from app.demo.data import seed_demo_catalog
from app.api.deps import (
    get_health_service,
    get_optional_provider_registry,
    get_provider_registry,
    get_search_rate_limiter,
    get_sync_rate_limiter,
    get_sync_job_scheduler,
)
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
    state = seed_demo_catalog(
        session,
        include_yandex_catalog_sections=include_yandex_catalog_sections,
    )
    return {
        "artist_id": state.artist_id,
        "release_id": state.release_id,
        "track_id": state.track_id,
        "candidate_release_id": state.candidate_release_id,
        "missing_release_id": state.missing_release_id,
    }
