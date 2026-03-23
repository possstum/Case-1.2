from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.config import Settings, clear_settings_cache
from app.api.deps import (
    get_health_service,
    get_optional_provider_registry,
    get_search_rate_limiter,
    get_search_refresh_scheduler,
)
from app.db.models import Artist, LinkArtist, PlatformArtist, SearchCache
from app.db.repositories.search_cache import SearchCacheRepository
from app.main import create_app
from app.providers import (
    MusicProvider,
    ProviderArtist,
    ProviderEntityKind,
    ProviderName,
    ProviderRegistry,
    ProviderSearchHit,
    ProviderSearchResult,
)
from app.utils.normalization import display_norm, match_norm
from tests.conftest import StubHealthService
from tests.test_support import make_track


def make_artist(
    provider: ProviderName,
    provider_id: str,
    name: str,
    *,
    aliases: list[str] | None = None,
) -> ProviderArtist:
    aliases = aliases or []
    return ProviderArtist(
        provider=provider,
        provider_id=provider_id,
        name=name,
        display_norm=display_norm(name),
        match_norm=match_norm(name),
        aliases=aliases,
        alias_match_norms=[match_norm(alias) for alias in aliases],
    )


class StubSearchProvider(MusicProvider):
    def __init__(
        self,
        *,
        provider_name: ProviderName,
        hits: list[ProviderSearchHit] | None = None,
        error: Exception | None = None,
        error_sequence: list[Exception | None] | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.hits = hits or []
        self.error = error
        self.error_sequence = list(error_sequence or [])
        self.search_calls = 0

    def search(
        self,
        query: str,
        *,
        limit: int | None,
        kind: Optional[ProviderEntityKind] = None,
    ) -> ProviderSearchResult:
        self.search_calls += 1
        if self.error_sequence:
            next_error = self.error_sequence.pop(0)
            if next_error is not None:
                raise next_error
        if self.error is not None:
            raise self.error
        items = self.hits
        if kind is not None:
            items = [hit for hit in items if hit.kind == kind]
        return ProviderSearchResult(query=query, items=items if limit is None else items[:limit])

    def get_artist(self, provider_id: str):
        raise NotImplementedError

    def get_release(self, provider_id: str):
        raise NotImplementedError

    def get_track(self, provider_id: str):
        raise NotImplementedError


class RecordingScheduler:
    def __init__(self, job_id: str = "job-refresh-1") -> None:
        self.job_id = job_id
        self.calls: list[dict[str, object]] = []

    def schedule(self, *, query: str, kind: Optional[str], limit: int | None) -> Optional[str]:
        self.calls.append({"query": query, "kind": kind, "limit": limit})
        return self.job_id


class AllowAllLimiter:
    def allow(self, **_: object) -> bool:
        return True


class DenyAllLimiter:
    def allow(self, **_: object) -> bool:
        return False


def create_search_client(
    *,
    provider_registry: ProviderRegistry,
    refresh_scheduler: RecordingScheduler,
    limiter,
) -> TestClient:
    application = create_app()
    application.dependency_overrides[get_health_service] = lambda: StubHealthService()
    application.dependency_overrides[get_optional_provider_registry] = lambda: provider_registry
    application.dependency_overrides[get_search_refresh_scheduler] = lambda: refresh_scheduler
    application.dependency_overrides[get_search_rate_limiter] = lambda: limiter
    return TestClient(application)


def seed_search_cache(
    db_session,
    *,
    response_json: dict[str, object],
    is_partial: bool,
    stale_at: datetime,
    expires_at: datetime,
    last_refreshed_at: datetime,
    cache_key: str = "search:v2:artist:5:krovostok",
    query_text: str = "Кровосток",
    normalized_query: str = "krovostok",
    kind: str = "artist",
) -> None:
    cache_repository = SearchCacheRepository(db_session)
    cache_repository.upsert(
        cache_key=cache_key,
        query_text=query_text,
        normalized_query=normalized_query,
        kind=kind,
        response_json=response_json,
        is_partial=is_partial,
        stale_at=stale_at,
        expires_at=expires_at,
        last_refreshed_at=last_refreshed_at,
    )
    db_session.commit()


def test_search_returns_fresh_cache_without_provider_calls(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    youtube = StubSearchProvider(provider_name=ProviderName.YOUTUBE)
    yandex = StubSearchProvider(provider_name=ProviderName.YANDEX)
    scheduler = RecordingScheduler()
    now = datetime.now(timezone.utc)
    seed_search_cache(
        db_session,
        response_json={
            "query": "Кровосток",
            "normalized_query": "krovostok",
            "kind": "artist",
            "partial": False,
            "missing_platforms": [],
            "results": [
                {
                    "kind": "artist",
                    "canonical_id": 1,
                    "decision": "auto",
                    "score": 0.99,
                    "features_json": {"seeded": True},
                    "platforms": {
                        "youtube": {
                            "provider": "youtube",
                            "provider_id": "yt-1",
                            "kind": "artist",
                            "label": "Кровосток",
                            "display_norm": "кровосток",
                            "match_norm": "krovostok",
                        },
                        "yandex": {
                            "provider": "yandex",
                            "provider_id": "ya-1",
                            "kind": "artist",
                            "label": "Krovostok",
                            "display_norm": "krovostok",
                            "match_norm": "krovostok",
                        },
                    },
                }
            ],
        },
        is_partial=False,
        stale_at=now + timedelta(minutes=5),
        expires_at=now + timedelta(minutes=30),
        last_refreshed_at=now,
    )

    with create_search_client(
        provider_registry=ProviderRegistry((youtube, yandex)),
        refresh_scheduler=scheduler,
        limiter=AllowAllLimiter(),
    ) as client:
        response = client.get("/search", params={"q": "Кровосток", "kind": "artist", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["cache"]["status"] == "fresh"
    assert payload["cache"]["refresh_queued"] is False
    assert payload["results"][0]["canonical_id"] == 1
    assert youtube.search_calls == 0
    assert yandex.search_calls == 0
    assert scheduler.calls == []


def test_search_returns_stale_cache_and_enqueues_refresh(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    youtube = StubSearchProvider(provider_name=ProviderName.YOUTUBE)
    yandex = StubSearchProvider(provider_name=ProviderName.YANDEX)
    scheduler = RecordingScheduler(job_id="refresh-42")
    now = datetime.now(timezone.utc)
    seed_search_cache(
        db_session,
        response_json={
            "query": "Кровосток",
            "normalized_query": "krovostok",
            "kind": "artist",
            "partial": False,
            "missing_platforms": [],
            "results": [],
        },
        is_partial=False,
        stale_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(minutes=30),
        last_refreshed_at=now - timedelta(minutes=10),
    )

    with create_search_client(
        provider_registry=ProviderRegistry((youtube, yandex)),
        refresh_scheduler=scheduler,
        limiter=AllowAllLimiter(),
    ) as client:
        response = client.get("/search", params={"q": "Кровосток", "kind": "artist", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["cache"]["status"] == "stale"
    assert payload["cache"]["refresh_queued"] is True
    assert payload["cache"]["refresh_job_id"] == "refresh-42"
    assert scheduler.calls == [{"query": "Кровосток", "kind": "artist", "limit": 5}]
    assert youtube.search_calls == 0
    assert yandex.search_calls == 0


def test_search_returns_fresh_cache_without_providers_configured(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    scheduler = RecordingScheduler(job_id="refresh-should-not-run")
    now = datetime.now(timezone.utc)
    seed_search_cache(
        db_session,
        response_json={
            "query": "Кровосток",
            "normalized_query": "krovostok",
            "kind": "artist",
            "partial": False,
            "missing_platforms": [],
            "results": [],
        },
        is_partial=False,
        stale_at=now + timedelta(minutes=5),
        expires_at=now + timedelta(minutes=30),
        last_refreshed_at=now,
    )

    with create_search_client(
        provider_registry=ProviderRegistry(()),
        refresh_scheduler=scheduler,
        limiter=AllowAllLimiter(),
    ) as client:
        response = client.get("/search", params={"q": "Кровосток", "kind": "artist", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["cache"]["status"] == "fresh"
    assert payload["cache"]["refresh_queued"] is False
    assert payload["cache"]["refresh_job_id"] is None
    assert scheduler.calls == []


def test_search_returns_stale_cache_without_refresh_when_providers_missing(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    scheduler = RecordingScheduler(job_id="refresh-should-not-run")
    now = datetime.now(timezone.utc)
    seed_search_cache(
        db_session,
        response_json={
            "query": "Кровосток",
            "normalized_query": "krovostok",
            "kind": "artist",
            "partial": False,
            "missing_platforms": [],
            "results": [],
        },
        is_partial=False,
        stale_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(minutes=30),
        last_refreshed_at=now - timedelta(minutes=10),
    )

    with create_search_client(
        provider_registry=ProviderRegistry(()),
        refresh_scheduler=scheduler,
        limiter=AllowAllLimiter(),
    ) as client:
        response = client.get("/search", params={"q": "Кровосток", "kind": "artist", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["cache"]["status"] == "stale"
    assert payload["cache"]["refresh_queued"] is False
    assert payload["cache"]["refresh_job_id"] is None
    assert scheduler.calls == []


def test_search_cold_miss_fetches_providers_persists_cache_and_links(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    youtube_artist = make_artist(ProviderName.YOUTUBE, "yt-1", "Кровосток")
    yandex_artist = make_artist(ProviderName.YANDEX, "ya-1", "Krovostok")
    youtube = StubSearchProvider(
        provider_name=ProviderName.YOUTUBE,
        hits=[ProviderSearchHit(kind=ProviderEntityKind.ARTIST, entity=youtube_artist)],
    )
    yandex = StubSearchProvider(
        provider_name=ProviderName.YANDEX,
        hits=[ProviderSearchHit(kind=ProviderEntityKind.ARTIST, entity=yandex_artist)],
    )

    with create_search_client(
        provider_registry=ProviderRegistry((youtube, yandex)),
        refresh_scheduler=RecordingScheduler(),
        limiter=AllowAllLimiter(),
    ) as client:
        response = client.get("/search", params={"q": "Кровосток", "kind": "artist", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["cache"]["status"] == "miss"
    assert payload["partial"] is False
    assert payload["results"][0]["decision"] == "auto"
    assert payload["results"][0]["canonical_id"] is not None

    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(SearchCache)) == 1
    assert db_session.scalar(select(func.count()).select_from(PlatformArtist)) == 2
    assert db_session.scalar(select(func.count()).select_from(Artist)) == 1
    assert db_session.scalar(select(func.count()).select_from(LinkArtist)) == 2


def test_search_track_without_limit_returns_full_provider_set_and_caches_all_key(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    yandex_tracks = [
        ProviderSearchHit(
            kind=ProviderEntityKind.TRACK,
            entity=make_track(
                ProviderName.YANDEX,
                f"ya-track-{index}",
                f"Трек {index}",
                artist_names=["Кровосток"],
                duration_ms=180000 + index,
            ),
        )
        for index in range(1, 13)
    ]
    yandex = StubSearchProvider(
        provider_name=ProviderName.YANDEX,
        hits=yandex_tracks,
    )

    with create_search_client(
        provider_registry=ProviderRegistry((yandex,)),
        refresh_scheduler=RecordingScheduler(),
        limiter=AllowAllLimiter(),
    ) as client:
        response = client.get("/search", params={"q": "Кровосток", "kind": "track"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["results"]) == 12
    assert payload["results"][0]["platforms"]["yandex"]["label"] == "Трек 1"
    assert db_session.scalar(select(SearchCache.cache_key)) == "search:v2:track:all:krovostok"


@pytest.mark.parametrize(
    ("query", "youtube_exact_name", "yandex_exact_name", "live_prefix"),
    [
        ("Krovostok", "Krovostok - Topic", "Krovostok", "Krovostok"),
        ("Motorama", "Motorama - Topic", "Motorama", "Motorama"),
    ],
)
def test_search_artist_query_rerank_prefers_exact_canonical_artist_over_noisier_match(
    sqlite_database_url: str,
    migrated_sqlite_database,
    query: str,
    youtube_exact_name: str,
    yandex_exact_name: str,
    live_prefix: str,
) -> None:
    youtube = StubSearchProvider(
        provider_name=ProviderName.YOUTUBE,
        hits=[
            ProviderSearchHit(
                kind=ProviderEntityKind.ARTIST,
                entity=make_artist(
                    ProviderName.YOUTUBE,
                    "yt-exact",
                    youtube_exact_name,
                    aliases=[query],
                ),
            ),
            ProviderSearchHit(
                kind=ProviderEntityKind.ARTIST,
                entity=make_artist(
                    ProviderName.YOUTUBE,
                    "yt-live",
                    f"{live_prefix} Live Archive",
                ),
            ),
        ],
    )
    yandex = StubSearchProvider(
        provider_name=ProviderName.YANDEX,
        hits=[
            ProviderSearchHit(
                kind=ProviderEntityKind.ARTIST,
                entity=make_artist(
                    ProviderName.YANDEX,
                    "ya-exact",
                    yandex_exact_name,
                ),
            ),
            ProviderSearchHit(
                kind=ProviderEntityKind.ARTIST,
                entity=make_artist(
                    ProviderName.YANDEX,
                    "ya-live-a",
                    f"{live_prefix} Live Archive",
                ),
            ),
            ProviderSearchHit(
                kind=ProviderEntityKind.ARTIST,
                entity=make_artist(
                    ProviderName.YANDEX,
                    "ya-live-b",
                    f"{live_prefix} Live Archive (Official)",
                ),
            ),
        ],
    )

    with create_search_client(
        provider_registry=ProviderRegistry((youtube, yandex)),
        refresh_scheduler=RecordingScheduler(),
        limiter=AllowAllLimiter(),
    ) as client:
        response = client.get("/search", params={"q": query, "kind": "artist", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["cache"]["status"] == "miss"

    exact_result = payload["results"][0]
    live_result = payload["results"][1]

    assert exact_result["kind"] == "artist"
    assert exact_result["canonical_id"] is not None
    assert exact_result["platforms"]["yandex"]["label"] == yandex_exact_name
    assert exact_result["score"] > live_result["score"]
    assert exact_result["features_json"]["search_rank_matching_score"] < live_result["features_json"]["search_rank_matching_score"]
    assert exact_result["features_json"]["search_rank_version"] == "artist_query_v1"
    assert exact_result["features_json"]["search_rank_best_platform"] == "yandex"
    assert exact_result["features_json"]["search_rank_query_match_norm"] == match_norm(query)
    assert "name_token_overlap" in exact_result["features_json"]
    assert "decision_reasons" in exact_result["features_json"]
    assert "search_rank_score" in exact_result["features_json"]


def test_search_ignores_old_v1_artist_cache_and_writes_v2_entry(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    now = datetime.now(timezone.utc)
    seed_search_cache(
        db_session,
        cache_key="search:v1:artist:5:krovostok",
        response_json={
            "query": "Krovostok",
            "normalized_query": "krovostok",
            "kind": "artist",
            "partial": False,
            "missing_platforms": [],
            "results": [
                {
                    "kind": "artist",
                    "canonical_id": 999,
                    "decision": "auto",
                    "score": 0.99,
                    "features_json": {"seeded": "old-cache"},
                    "platforms": {
                        "youtube": None,
                        "yandex": {
                            "provider": "yandex",
                            "provider_id": "ya-stale",
                            "kind": "artist",
                            "label": "Stale Artist",
                            "display_norm": "stale artist",
                            "match_norm": "stale artist",
                        },
                    },
                }
            ],
        },
        is_partial=False,
        stale_at=now + timedelta(minutes=5),
        expires_at=now + timedelta(minutes=30),
        last_refreshed_at=now,
    )
    youtube = StubSearchProvider(
        provider_name=ProviderName.YOUTUBE,
        hits=[ProviderSearchHit(kind=ProviderEntityKind.ARTIST, entity=make_artist(ProviderName.YOUTUBE, "yt-1", "Krovostok"))],
    )
    yandex = StubSearchProvider(
        provider_name=ProviderName.YANDEX,
        hits=[ProviderSearchHit(kind=ProviderEntityKind.ARTIST, entity=make_artist(ProviderName.YANDEX, "ya-1", "Krovostok"))],
    )

    with create_search_client(
        provider_registry=ProviderRegistry((youtube, yandex)),
        refresh_scheduler=RecordingScheduler(),
        limiter=AllowAllLimiter(),
    ) as client:
        response = client.get("/search", params={"q": "Krovostok", "kind": "artist", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["cache"]["status"] == "miss"
    assert payload["results"][0]["canonical_id"] != 999
    assert youtube.search_calls == 1
    assert yandex.search_calls == 1

    db_session.expire_all()
    assert db_session.scalar(select(func.count()).select_from(SearchCache)) == 2
    assert (
        db_session.scalar(select(SearchCache).where(SearchCache.cache_key == "search:v2:artist:5:krovostok")) is not None
    )


def test_search_artist_warm_cache_replays_same_primary_result_and_score(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    youtube = StubSearchProvider(
        provider_name=ProviderName.YOUTUBE,
        hits=[
            ProviderSearchHit(
                kind=ProviderEntityKind.ARTIST,
                entity=make_artist(
                    ProviderName.YOUTUBE,
                    "yt-exact",
                    "Motorama - Topic",
                    aliases=["Motorama"],
                ),
            ),
            ProviderSearchHit(
                kind=ProviderEntityKind.ARTIST,
                entity=make_artist(
                    ProviderName.YOUTUBE,
                    "yt-live",
                    "Motorama Live Archive",
                ),
            ),
        ],
    )
    yandex = StubSearchProvider(
        provider_name=ProviderName.YANDEX,
        hits=[
            ProviderSearchHit(kind=ProviderEntityKind.ARTIST, entity=make_artist(ProviderName.YANDEX, "ya-exact", "Motorama")),
            ProviderSearchHit(kind=ProviderEntityKind.ARTIST, entity=make_artist(ProviderName.YANDEX, "ya-live-a", "Motorama Live Archive")),
            ProviderSearchHit(
                kind=ProviderEntityKind.ARTIST,
                entity=make_artist(ProviderName.YANDEX, "ya-live-b", "Motorama Live Archive (Official)"),
            ),
        ],
    )

    with create_search_client(
        provider_registry=ProviderRegistry((youtube, yandex)),
        refresh_scheduler=RecordingScheduler(),
        limiter=AllowAllLimiter(),
    ) as client:
        first_response = client.get("/search", params={"q": "Motorama", "kind": "artist", "limit": 5})
        second_response = client.get("/search", params={"q": "Motorama", "kind": "artist", "limit": 5})

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_payload = first_response.json()
    second_payload = second_response.json()
    first_top = first_payload["results"][0]
    second_top = second_payload["results"][0]

    assert first_payload["cache"]["status"] == "miss"
    assert second_payload["cache"]["status"] == "fresh"
    assert first_top["canonical_id"] == second_top["canonical_id"]
    assert first_top["platforms"]["youtube"]["provider_id"] == second_top["platforms"]["youtube"]["provider_id"]
    assert first_top["platforms"]["yandex"]["provider_id"] == second_top["platforms"]["yandex"]["provider_id"]
    assert first_top["score"] == second_top["score"]
    assert first_top["features_json"]["search_rank_version"] == "artist_query_v1"
    assert second_top["features_json"]["search_rank_version"] == "artist_query_v1"
    assert youtube.search_calls == 1
    assert yandex.search_calls == 1


def test_search_returns_partial_response_when_provider_fails(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    youtube_artist = make_artist(ProviderName.YOUTUBE, "yt-1", "Motorama")
    youtube = StubSearchProvider(
        provider_name=ProviderName.YOUTUBE,
        hits=[ProviderSearchHit(kind=ProviderEntityKind.ARTIST, entity=youtube_artist)],
    )
    yandex = StubSearchProvider(
        provider_name=ProviderName.YANDEX,
        error=RuntimeError("provider down"),
    )

    with create_search_client(
        provider_registry=ProviderRegistry((youtube, yandex)),
        refresh_scheduler=RecordingScheduler(),
        limiter=AllowAllLimiter(),
    ) as client:
        response = client.get("/search", params={"q": "Motorama", "kind": "artist", "limit": 5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["partial"] is True
    assert payload["missing_platforms"] == ["yandex"]
    assert payload["results"][0]["decision"] == "reject"
    assert payload["results"][0]["platforms"]["youtube"]["provider_id"] == "yt-1"
    assert payload["results"][0]["platforms"]["yandex"] is None

    db_session.expire_all()
    cache_entry = db_session.scalar(select(SearchCache))
    assert cache_entry is not None
    assert cache_entry.is_partial is True


def test_search_returns_503_when_no_providers_and_cache_misses(
    sqlite_database_url: str,
    migrated_sqlite_database,
) -> None:
    with create_search_client(
        provider_registry=ProviderRegistry(()),
        refresh_scheduler=RecordingScheduler(),
        limiter=AllowAllLimiter(),
    ) as client:
        response = client.get("/search", params={"q": "Motorama", "kind": "artist", "limit": 5})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "search_providers_unavailable"


def test_search_returns_503_when_no_providers_and_cache_is_expired(
    sqlite_database_url: str,
    migrated_sqlite_database,
    db_session,
) -> None:
    now = datetime.now(timezone.utc)
    seed_search_cache(
        db_session,
        response_json={
            "query": "Кровосток",
            "normalized_query": "krovostok",
            "kind": "artist",
            "partial": False,
            "missing_platforms": [],
            "results": [],
        },
        is_partial=False,
        stale_at=now - timedelta(minutes=10),
        expires_at=now - timedelta(seconds=1),
        last_refreshed_at=now - timedelta(minutes=20),
    )

    with create_search_client(
        provider_registry=ProviderRegistry(()),
        refresh_scheduler=RecordingScheduler(),
        limiter=AllowAllLimiter(),
    ) as client:
        response = client.get("/search", params={"q": "Кровосток", "kind": "artist", "limit": 5})

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "search_providers_unavailable"


def test_optional_provider_registry_includes_public_yandex_without_token(
    sqlite_database_url: str,
    migrated_sqlite_database,
) -> None:
    clear_settings_cache()

    provider_registry = get_optional_provider_registry(
        settings=Settings(
            YOUTUBE_MUSIC_TOKEN=None,
            YANDEX_MUSIC_TOKEN=None,
        )
    )

    assert provider_registry is not None
    assert [provider.provider_name.value for provider in provider_registry.all()] == ["yandex"]


def test_search_rate_limit_returns_429(
    sqlite_database_url: str,
    migrated_sqlite_database,
) -> None:
    youtube = StubSearchProvider(provider_name=ProviderName.YOUTUBE)
    yandex = StubSearchProvider(provider_name=ProviderName.YANDEX)
    headers = {"X-Correlation-ID": "cid-search-rate-limit"}

    with create_search_client(
        provider_registry=ProviderRegistry((youtube, yandex)),
        refresh_scheduler=RecordingScheduler(),
        limiter=DenyAllLimiter(),
    ) as client:
        response = client.get(
            "/search",
            params={"q": "Krovostok", "kind": "artist", "limit": 5},
            headers=headers,
        )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limit_exceeded"
    assert response.headers["X-Correlation-ID"] == headers["X-Correlation-ID"]
    assert response.json()["error"]["correlation_id"] == headers["X-Correlation-ID"]


def test_search_retries_provider_when_attempts_are_configured(
    sqlite_database_url: str,
    migrated_sqlite_database,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SEARCH_PROVIDER_MAX_ATTEMPTS", "2")
    monkeypatch.setenv("SEARCH_PROVIDER_RETRY_BACKOFF_SECONDS", "0")
    clear_settings_cache()

    youtube = StubSearchProvider(
        provider_name=ProviderName.YOUTUBE,
        hits=[ProviderSearchHit(kind=ProviderEntityKind.ARTIST, entity=make_artist(ProviderName.YOUTUBE, "yt-1", "Motorama"))],
        error_sequence=[RuntimeError("temporary provider failure"), None],
    )
    yandex = StubSearchProvider(provider_name=ProviderName.YANDEX)

    try:
        with create_search_client(
            provider_registry=ProviderRegistry((youtube, yandex)),
            refresh_scheduler=RecordingScheduler(),
            limiter=AllowAllLimiter(),
        ) as client:
            response = client.get("/search", params={"q": "Motorama", "kind": "artist", "limit": 5})
    finally:
        clear_settings_cache()

    assert response.status_code == 200
    assert youtube.search_calls == 2
