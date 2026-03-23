from __future__ import annotations

from app.core.config import get_settings
from app.db.session import get_session_factory
from app.providers import ProviderName, ProviderRegistry
from app.providers.youtube_music.client import YouTubeMusicClient
from app.providers.yandex_music.client import YandexMusicClient
from app.services.artist_service import ArtistService
from app.services.link_service import LinkService
from app.services.release_service import ReleaseService
from app.services.sync_service import SyncService
from app.services.track_service import TrackService
from app.services.yandex_catalog_service import YandexCatalogIngestionService


def run_sync_job(job_id: str) -> dict[str, object]:
    session_factory = get_session_factory()
    session = session_factory()
    try:
        settings = get_settings()
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
        provider_registry = ProviderRegistry(providers=tuple(providers))
        link_service = LinkService(session)
        yandex_provider = provider_registry.get(ProviderName.YANDEX.value)
        yandex_catalog_ingestion_service = None
        if yandex_provider is not None:
            yandex_catalog_ingestion_service = YandexCatalogIngestionService(
                session=session,
                provider=yandex_provider,
                link_service=link_service,
            )
        sync_service = SyncService(
            session=session,
            settings=settings,
            provider_registry=provider_registry,
            link_service=link_service,
            artist_service=ArtistService(session),
            release_service=ReleaseService(session),
            track_service=TrackService(session),
            yandex_catalog_ingestion_service=yandex_catalog_ingestion_service,
        )
        return sync_service.execute(job_id).model_dump(mode="json")
    finally:
        session.close()
