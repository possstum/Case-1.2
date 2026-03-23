from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Optional, Protocol

from sqlalchemy.orm import Session

from app.api.schemas.jobs import SyncJobResponse
from app.api.schemas.sync import SyncEnqueueResponse
from app.core.config import Settings
from app.core.errors import NotFoundError, ServiceUnavailableError
from app.db.models import SyncJob
from app.db.repositories.sync_jobs import SyncJobRepository
from app.providers import ProviderEntityKind, ProviderName, ProviderRegistry
from app.services.artist_service import ArtistService
from app.services.link_service import LinkService
from app.services.release_service import ReleaseService
from app.services.track_service import TrackService
from app.services.yandex_catalog_service import (
    YandexCatalogIngestionService,
    YandexCatalogIngestionSummary,
)

logger = logging.getLogger(__name__)


class SyncJobScheduler(Protocol):
    def schedule(
        self,
        *,
        job_id: str,
        queue_name: str,
    ) -> Optional[str]:
        ...


class SyncService:
    def __init__(
        self,
        *,
        session: Session,
        settings: Settings,
        provider_registry: ProviderRegistry,
        link_service: LinkService,
        artist_service: ArtistService,
        release_service: ReleaseService,
        track_service: TrackService,
        yandex_catalog_ingestion_service: Optional[YandexCatalogIngestionService] = None,
        job_scheduler: Optional[SyncJobScheduler] = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.provider_registry = provider_registry
        self.link_service = link_service
        self.artist_service = artist_service
        self.release_service = release_service
        self.track_service = track_service
        self.yandex_catalog_ingestion_service = yandex_catalog_ingestion_service
        self.job_scheduler = job_scheduler
        self.sync_job_repository = SyncJobRepository(session)

    def enqueue(self, *, kind: str, target_id: int) -> SyncEnqueueResponse:
        self._ensure_target_exists(kind=kind, target_id=target_id)
        existing_job = self.sync_job_repository.get_active_for_target(
            kind=kind,
            target_id=str(target_id),
        )
        if existing_job is not None:
            self.session.commit()
            return SyncEnqueueResponse(created=False, job=self._to_job_response(existing_job))

        sync_job = self.sync_job_repository.create(
            kind=kind,
            target_id=str(target_id),
            queue_name=self.settings.rq_default_queue,
            payload_json={"kind": kind, "target_id": str(target_id)},
        )
        if self.job_scheduler is None:
            raise ServiceUnavailableError("sync scheduler is not configured", code="sync_scheduler_unavailable")

        rq_job_id = self.job_scheduler.schedule(
            job_id=sync_job.id,
            queue_name=sync_job.queue_name,
        )
        if rq_job_id is None:
            self.sync_job_repository.mark_failed(
                sync_job,
                error_json={"reason": "queue_enqueue_failed"},
            )
            self.session.commit()
            raise ServiceUnavailableError("sync queue is unavailable", code="sync_queue_unavailable")

        self.sync_job_repository.set_rq_job_id(sync_job, rq_job_id=rq_job_id)
        self.session.commit()
        return SyncEnqueueResponse(created=True, job=self._to_job_response(sync_job))

    def get_job(self, job_id: str) -> SyncJobResponse:
        sync_job = self.sync_job_repository.get(job_id)
        if sync_job is None:
            raise NotFoundError(f"job {job_id} not found")
        return self._to_job_response(sync_job)

    def execute(self, job_id: str) -> SyncJobResponse:
        sync_job = self.sync_job_repository.get(job_id)
        if sync_job is None:
            raise NotFoundError(f"job {job_id} not found")
        if sync_job.status in {"finished", "failed"}:
            return self._to_job_response(sync_job)

        self.sync_job_repository.mark_started(sync_job)
        self.session.commit()
        try:
            links = self._load_target_links(kind=sync_job.kind, target_id=int(sync_job.target_id))
            if not links:
                self.sync_job_repository.mark_failed(
                    sync_job,
                    error_json={"reason": "no_platform_links", "kind": sync_job.kind, "target_id": sync_job.target_id},
                )
                self.session.commit()
                return self._to_job_response(sync_job)

            provider_results: list[dict[str, Any]] = []
            updated_count = 0
            for provider_name, provider_id in links:
                try:
                    refresh_result, attempts = self._refresh_provider_target(
                        kind=sync_job.kind,
                        provider_name=provider_name,
                        provider_id=provider_id,
                    )
                    provider_result = {
                        "provider": provider_name,
                        "provider_id": provider_id,
                        "status": "updated",
                        "attempts": attempts,
                    }
                    provider_result.update(refresh_result)
                    provider_results.append(provider_result)
                    updated_count += 1
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "sync_provider_failed kind=%s target_id=%s provider=%s error=%s",
                        sync_job.kind,
                        sync_job.target_id,
                        provider_name,
                        exc.__class__.__name__,
                    )
                    provider_results.append(
                        {
                            "provider": provider_name,
                            "provider_id": provider_id,
                            "status": "failed",
                            "error": str(exc),
                        }
                    )

            if updated_count == 0:
                self.sync_job_repository.mark_failed(
                    sync_job,
                    error_json={
                        "reason": "provider_refresh_failed",
                        "providers": provider_results,
                    },
                )
                self.session.commit()
                return self._to_job_response(sync_job)

            self.sync_job_repository.mark_finished(
                sync_job,
                result_json={
                    "kind": sync_job.kind,
                    "target_id": sync_job.target_id,
                    "updated_count": updated_count,
                    "partial": updated_count < len(provider_results),
                    "providers": provider_results,
                },
            )
            self.session.commit()
            return self._to_job_response(sync_job)
        except Exception as exc:  # noqa: BLE001
            self.sync_job_repository.mark_failed(
                sync_job,
                error_json={
                    "reason": "sync_execution_failed",
                    "error": str(exc),
                },
            )
            self.session.commit()
            return self._to_job_response(sync_job)

    def _ensure_target_exists(self, *, kind: str, target_id: int) -> None:
        if kind == ProviderEntityKind.ARTIST.value:
            self.artist_service.get_artist_model(target_id)
            return
        if kind == ProviderEntityKind.RELEASE.value:
            self.release_service.get_release_model(target_id)
            return
        if kind == ProviderEntityKind.TRACK.value:
            self.track_service.get_track_model(target_id)
            return
        raise NotFoundError(f"unsupported sync kind {kind}")

    def _load_target_links(self, *, kind: str, target_id: int) -> list[tuple[str, str]]:
        if kind == ProviderEntityKind.ARTIST.value:
            artist = self.artist_service.get_artist_model(target_id)
            return [
                (link.platform_artist.platform, link.platform_artist.platform_id)
                for link in artist.platform_links
            ]
        if kind == ProviderEntityKind.RELEASE.value:
            release = self.release_service.get_release_model(target_id)
            return [
                (link.platform_release.platform, link.platform_release.platform_id)
                for link in release.platform_links
            ]
        if kind == ProviderEntityKind.TRACK.value:
            track = self.track_service.get_track_model(target_id)
            return [
                (link.platform_track.platform, link.platform_track.platform_id)
                for link in track.platform_links
            ]
        raise NotFoundError(f"unsupported sync kind {kind}")

    def _refresh_provider_target(
        self,
        *,
        kind: str,
        provider_name: str,
        provider_id: str,
    ) -> tuple[dict[str, Any], int]:
        provider = self.provider_registry.get(provider_name)
        if provider is None:
            raise RuntimeError(f"provider {provider_name} is not configured")

        attempts = max(1, self.settings.sync_provider_max_attempts)
        backoff_seconds = max(0.0, self.settings.sync_provider_retry_backoff_seconds)
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            try:
                return self._call_refresh_with_timeout(
                    provider=provider,
                    kind=kind,
                    provider_id=provider_id,
                ), attempt
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == attempts:
                    break
                if backoff_seconds > 0:
                    time.sleep(backoff_seconds)
        assert last_error is not None
        raise last_error

    def _call_refresh_with_timeout(self, *, provider, kind: str, provider_id: str) -> dict[str, Any]:
        if self._should_use_yandex_catalog_ingestion(provider=provider):
            provider_method = self._make_yandex_ingest_callable(kind=kind)
        elif kind == ProviderEntityKind.ARTIST.value:
            provider_method = provider.get_artist
        elif kind == ProviderEntityKind.RELEASE.value:
            provider_method = provider.get_release
        else:
            provider_method = provider.get_track

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(provider_method, provider_id)
        try:
            result = future.result(timeout=self.settings.sync_provider_timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise TimeoutError(f"{provider.provider_name.value} timed out") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
        if self._should_use_yandex_catalog_ingestion(provider=provider):
            return result
        self.link_service.persist_platform_entity(result)
        return {"mode": "entity_refresh"}

    def _should_use_yandex_catalog_ingestion(self, *, provider) -> bool:
        return (
            provider.provider_name.value == ProviderName.YANDEX.value
            and self.yandex_catalog_ingestion_service is not None
        )

    def _make_yandex_ingest_callable(self, *, kind: str):
        assert self.yandex_catalog_ingestion_service is not None
        if kind == ProviderEntityKind.ARTIST.value:
            return self._ingest_yandex_artist
        if kind == ProviderEntityKind.RELEASE.value:
            return self._ingest_yandex_release
        return self._ingest_yandex_track

    def _ingest_yandex_artist(self, provider_id: str) -> dict[str, Any]:
        assert self.yandex_catalog_ingestion_service is not None
        summary = self.yandex_catalog_ingestion_service.ingest_artist(provider_id)
        return self._yandex_summary_payload(summary)

    def _ingest_yandex_release(self, provider_id: str) -> dict[str, Any]:
        assert self.yandex_catalog_ingestion_service is not None
        release = self.yandex_catalog_ingestion_service.ingest_release(provider_id)
        return {
            "mode": "catalog_ingest",
            "platform_release_id": release.id,
            "platform_release_provider_id": release.platform_id,
        }

    def _ingest_yandex_track(self, provider_id: str) -> dict[str, Any]:
        assert self.yandex_catalog_ingestion_service is not None
        track = self.yandex_catalog_ingestion_service.ingest_track(provider_id)
        return {
            "mode": "catalog_ingest",
            "platform_track_id": track.id,
            "platform_track_provider_id": track.platform_id,
        }

    def _yandex_summary_payload(self, summary: YandexCatalogIngestionSummary) -> dict[str, Any]:
        return {
            "mode": "catalog_ingest",
            "catalog_artist_provider_id": summary.artist_provider_id,
            "platform_artist_count": len(summary.platform_artist_ids),
            "platform_release_count": len(summary.platform_release_ids),
            "platform_track_count": len(summary.platform_track_ids),
            "catalog_list_count": len(summary.catalog_list_ids),
        }

    def _to_job_response(self, sync_job: SyncJob) -> SyncJobResponse:
        return SyncJobResponse(
            id=sync_job.id,
            kind=sync_job.kind,
            target_id=sync_job.target_id,
            status=sync_job.status,
            queue_name=sync_job.queue_name,
            attempts=sync_job.attempts,
            payload_json=sync_job.payload_json,
            result_json=sync_job.result_json,
            error_json=sync_job.error_json,
            started_at=sync_job.started_at,
            finished_at=sync_job.finished_at,
            created_at=sync_job.created_at,
            updated_at=sync_job.updated_at,
        )
