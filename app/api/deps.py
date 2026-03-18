from __future__ import annotations

from collections.abc import Generator
from typing import Optional

from fastapi import Depends, Request
from redis import Redis
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.errors import RateLimitExceededError, ServiceUnavailableError
from app.core.config import Settings, get_settings
from app.db.session import get_engine, get_redis_client, get_session_factory
from app.providers import ProviderName, ProviderRegistry
from app.providers.youtube_music.client import YouTubeMusicClient
from app.providers.yandex_music.client import YandexMusicClient
from app.services.artist_service import ArtistService
from app.services.release_service import ReleaseService
from app.services.track_service import TrackService
from app.services.link_service import LinkService
from app.services.matching_service import MatchingService
from app.services.health_service import HealthService
from app.services.search_service import SearchRefreshScheduler, SearchService
from app.services.sync_service import SyncJobScheduler, SyncService
from app.services.yandex_catalog_service import YandexCatalogIngestionService
from app.tasks.queue import RQSyncJobScheduler
from app.utils.rate_limit import FixedWindowRateLimiter


class NoOpSearchRefreshScheduler:
    def schedule(
        self,
        *,
        query: str,
        kind: str | None,
        limit: int,
    ) -> str | None:
        return None


def get_app_settings() -> Settings:
    return get_settings()


def get_db_engine() -> Engine:
    return get_engine()


def get_db_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def get_redis() -> Redis:
    return get_redis_client()


def get_health_service(
    settings: Settings = Depends(get_app_settings),
    engine: Engine = Depends(get_db_engine),
    redis_client: Redis = Depends(get_redis),
) -> HealthService:
    return HealthService(
        engine=engine,
        redis_client=redis_client,
        require_redis=settings.health_require_redis,
    )


def get_optional_provider_registry(
    settings: Settings = Depends(get_app_settings),
) -> Optional[ProviderRegistry]:
    providers = []
    if settings.youtube_music_token:
        providers.append(
            YouTubeMusicClient(
                token=settings.youtube_music_token,
                timeout_seconds=settings.provider_http_timeout_seconds,
            )
        )
    providers.append(
        YandexMusicClient(
            token=settings.yandex_music_token,
            timeout_seconds=settings.provider_http_timeout_seconds,
        )
    )
    if not providers:
        return None
    return ProviderRegistry(tuple(providers))


def get_provider_registry(
    provider_registry: Optional[ProviderRegistry] = Depends(get_optional_provider_registry),
) -> ProviderRegistry:
    if provider_registry is None:
        raise ServiceUnavailableError(
            "search providers are not configured",
            code="search_providers_unavailable",
        )
    return provider_registry


def get_search_rate_limiter(
    redis_client: Redis = Depends(get_redis),
) -> FixedWindowRateLimiter:
    return FixedWindowRateLimiter(redis_client=redis_client)


def get_sync_rate_limiter(
    redis_client: Redis = Depends(get_redis),
) -> FixedWindowRateLimiter:
    return FixedWindowRateLimiter(redis_client=redis_client)


def get_search_refresh_scheduler() -> SearchRefreshScheduler:
    return NoOpSearchRefreshScheduler()


def _build_search_service(
    *,
    session: Session,
    settings: Settings,
    provider_registry: ProviderRegistry,
    refresh_scheduler: SearchRefreshScheduler,
) -> SearchService:
    return SearchService(
        session=session,
        settings=settings,
        provider_registry=provider_registry,
        matching_service=MatchingService(),
        link_service=LinkService(session),
        refresh_scheduler=refresh_scheduler,
    )


def get_search_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    provider_registry: Optional[ProviderRegistry] = Depends(get_optional_provider_registry),
    refresh_scheduler: SearchRefreshScheduler = Depends(get_search_refresh_scheduler),
) -> SearchService:
    return _build_search_service(
        session=session,
        settings=settings,
        provider_registry=provider_registry if provider_registry is not None else ProviderRegistry(()),
        refresh_scheduler=refresh_scheduler,
    )


def get_web_search_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    provider_registry: Optional[ProviderRegistry] = Depends(get_optional_provider_registry),
    refresh_scheduler: SearchRefreshScheduler = Depends(get_search_refresh_scheduler),
) -> SearchService:
    return _build_search_service(
        session=session,
        settings=settings,
        provider_registry=provider_registry if provider_registry is not None else ProviderRegistry(()),
        refresh_scheduler=refresh_scheduler,
    )


def get_sync_provider_registry(
    settings: Settings = Depends(get_app_settings),
) -> ProviderRegistry:
    providers = []
    if settings.youtube_music_token:
        providers.append(
            YouTubeMusicClient(
                token=settings.youtube_music_token,
                timeout_seconds=settings.provider_http_timeout_seconds,
            )
        )
    providers.append(
        YandexMusicClient(
            token=settings.yandex_music_token,
            timeout_seconds=settings.provider_http_timeout_seconds,
        )
    )
    return ProviderRegistry(tuple(providers))


def _client_identifier(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _enforce_rate_limit(
    request: Request,
    *,
    limiter: FixedWindowRateLimiter,
    namespace: str,
    limit: int,
    window_seconds: int,
) -> None:
    allowed = limiter.allow(
        namespace=namespace,
        identifier=_client_identifier(request),
        limit=limit,
        window_seconds=window_seconds,
    )
    if not allowed:
        raise RateLimitExceededError()


def enforce_search_rate_limit(
    request: Request,
    limiter: FixedWindowRateLimiter = Depends(get_search_rate_limiter),
    settings: Settings = Depends(get_app_settings),
) -> None:
    _enforce_rate_limit(
        request,
        limiter=limiter,
        namespace="search",
        limit=settings.search_rate_limit,
        window_seconds=settings.search_rate_window_seconds,
    )


def enforce_sync_rate_limit(
    request: Request,
    limiter: FixedWindowRateLimiter = Depends(get_sync_rate_limiter),
    settings: Settings = Depends(get_app_settings),
) -> None:
    _enforce_rate_limit(
        request,
        limiter=limiter,
        namespace="sync",
        limit=settings.sync_rate_limit,
        window_seconds=settings.sync_rate_window_seconds,
    )


def get_artist_service(
    session: Session = Depends(get_db_session),
) -> ArtistService:
    return ArtistService(session)


def get_release_service(
    session: Session = Depends(get_db_session),
) -> ReleaseService:
    return ReleaseService(session)


def get_track_service(
    session: Session = Depends(get_db_session),
) -> TrackService:
    return TrackService(session)


def get_sync_job_scheduler() -> SyncJobScheduler:
    return RQSyncJobScheduler()


def get_sync_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_app_settings),
    provider_registry: ProviderRegistry = Depends(get_sync_provider_registry),
    job_scheduler: SyncJobScheduler = Depends(get_sync_job_scheduler),
) -> SyncService:
    link_service = LinkService(session)
    yandex_provider = provider_registry.get(ProviderName.YANDEX.value)
    yandex_catalog_ingestion_service = None
    if yandex_provider is not None:
        yandex_catalog_ingestion_service = YandexCatalogIngestionService(
            session=session,
            provider=yandex_provider,
            link_service=link_service,
        )
    return SyncService(
        session=session,
        settings=settings,
        provider_registry=provider_registry,
        link_service=link_service,
        artist_service=ArtistService(session),
        release_service=ReleaseService(session),
        track_service=TrackService(session),
        yandex_catalog_ingestion_service=yandex_catalog_ingestion_service,
        job_scheduler=job_scheduler,
    )
