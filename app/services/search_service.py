from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Protocol

from sqlalchemy.orm import Session

from app.api.schemas.search import (
    SearchCacheMetadata,
    SearchPlatformEntityPayload,
    SearchResponse,
    SearchResultItemPayload,
)
from app.core.config import Settings
from app.core.errors import ServiceUnavailableError
from app.db.repositories.search_cache import SearchCacheRepository
from app.providers import ProviderEntityKind, ProviderRegistry
from app.providers.base import ProviderArtist, ProviderEntity, ProviderRelease, ProviderSearchResult, ProviderTrack
from app.services.link_service import LinkService
from app.services.matching_service import MatchDecision, MatchingService
from app.utils.normalization import match_norm

logger = logging.getLogger(__name__)


class SearchRefreshScheduler(Protocol):
    def schedule(
        self,
        *,
        query: str,
        kind: Optional[str],
        limit: int,
    ) -> Optional[str]:
        ...


@dataclass(frozen=True)
class SearchContext:
    query: str
    normalized_query: str
    kind: Optional[str]
    limit: int
    now: datetime
    cache_key: str


class SearchService:
    def __init__(
        self,
        *,
        session: Session,
        settings: Settings,
        provider_registry: ProviderRegistry,
        matching_service: MatchingService,
        link_service: LinkService,
        refresh_scheduler: SearchRefreshScheduler,
    ) -> None:
        self.session = session
        self.settings = settings
        self.provider_registry = provider_registry
        self.matching_service = matching_service
        self.link_service = link_service
        self.refresh_scheduler = refresh_scheduler
        self.search_cache_repository = SearchCacheRepository(session)

    def search(
        self,
        *,
        query: str,
        kind: Optional[str],
        limit: Optional[int] = None,
    ) -> SearchResponse:
        validated_limit = self._normalize_limit(limit)
        normalized_query = match_norm(query)
        context = SearchContext(
            query=query,
            normalized_query=normalized_query,
            kind=kind,
            limit=validated_limit,
            now=datetime.now(timezone.utc),
            cache_key=self._build_cache_key(normalized_query=normalized_query, kind=kind, limit=validated_limit),
        )

        cache_entry = self.search_cache_repository.get_by_key(context.cache_key)
        if cache_entry and not self._is_expired(cache_entry, context.now):
            self.search_cache_repository.mark_hit(cache_entry)
            refresh_job_id = None
            refresh_queued = False
            cache_status = "fresh"
            if self._is_stale(cache_entry, context.now):
                cache_status = "stale"
                if self._has_providers():
                    refresh_job_id = self.refresh_scheduler.schedule(
                        query=context.query,
                        kind=context.kind,
                        limit=context.limit,
                    )
                    refresh_queued = refresh_job_id is not None
            self.session.commit()
            return self._response_from_cache(
                cache_entry.response_json,
                cache_status=cache_status,
                hit_count=cache_entry.hit_count,
                last_refreshed_at=cache_entry.last_refreshed_at,
                stale_at=cache_entry.stale_at,
                expires_at=cache_entry.expires_at,
                refresh_queued=refresh_queued,
                refresh_job_id=refresh_job_id,
            )

        if not self._has_providers():
            raise ServiceUnavailableError(
                "search providers are not configured",
                code="search_providers_unavailable",
            )

        response = self._execute_live_search(context)
        cache_entry = self.search_cache_repository.upsert(
            cache_key=context.cache_key,
            query_text=context.query,
            normalized_query=context.normalized_query,
            kind=context.kind,
            response_json=response.model_dump(mode="json", exclude={"cache"}),
            is_partial=response.partial,
            stale_at=context.now + timedelta(seconds=self.settings.search_cache_stale_seconds),
            expires_at=context.now + timedelta(seconds=self.settings.search_cache_ttl_seconds),
            last_refreshed_at=context.now,
        )
        self.session.commit()
        return response.model_copy(
            update={
                "cache": SearchCacheMetadata(
                    status="miss",
                    hit_count=cache_entry.hit_count,
                    last_refreshed_at=self._coerce_aware(cache_entry.last_refreshed_at),
                    stale_at=self._coerce_aware(cache_entry.stale_at),
                    expires_at=self._coerce_aware(cache_entry.expires_at),
                    refresh_queued=False,
                    refresh_job_id=None,
                )
            }
        )

    def _execute_live_search(self, context: SearchContext) -> SearchResponse:
        provider_results, missing_platforms = self._fan_out_provider_search(context)
        results = self._merge_search_results(provider_results)
        return SearchResponse(
            query=context.query,
            normalized_query=context.normalized_query,
            kind=context.kind,
            partial=bool(missing_platforms),
            missing_platforms=missing_platforms,
            cache=SearchCacheMetadata(status="miss"),
            results=results,
        )

    def _fan_out_provider_search(
        self,
        context: SearchContext,
    ) -> tuple[dict[str, ProviderSearchResult], list[str]]:
        provider_results: dict[str, ProviderSearchResult] = {}
        missing_platforms: list[str] = []
        providers = self.provider_registry.all()

        with ThreadPoolExecutor(max_workers=max(1, len(providers))) as executor:
            future_map = {
                executor.submit(
                    self._search_provider_with_retries,
                    provider,
                    context,
                ): provider
                for provider in providers
            }

            done, not_done = wait(
                future_map.keys(),
                timeout=self.settings.search_provider_timeout_seconds,
            )

            for future in done:
                provider = future_map[future]
                try:
                    provider_results[provider.provider_name.value] = future.result()
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "search_provider_failed provider=%s error=%s",
                        provider.provider_name.value,
                        exc.__class__.__name__,
                    )
                    missing_platforms.append(provider.provider_name.value)

            for future in not_done:
                provider = future_map[future]
                future.cancel()
                logger.warning("search_provider_timeout provider=%s", provider.provider_name.value)
                missing_platforms.append(provider.provider_name.value)

        for provider in providers:
            provider_name = provider.provider_name.value
            if provider_name not in provider_results and provider_name not in missing_platforms:
                missing_platforms.append(provider_name)
        return provider_results, sorted(missing_platforms)

    def _search_provider_with_retries(
        self,
        provider,
        context: SearchContext,
    ) -> ProviderSearchResult:
        attempts = max(1, self.settings.search_provider_max_attempts)
        backoff_seconds = max(0.0, self.settings.search_provider_retry_backoff_seconds)
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                return provider.search(
                    context.query,
                    limit=context.limit,
                    kind=ProviderEntityKind(context.kind) if context.kind else None,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == attempts:
                    break
                if backoff_seconds > 0:
                    time.sleep(backoff_seconds)

        assert last_error is not None
        raise last_error

    def _merge_search_results(
        self,
        provider_results: dict[str, ProviderSearchResult],
    ) -> list[SearchResultItemPayload]:
        grouped_results = {
            ProviderEntityKind.ARTIST.value: {},
            ProviderEntityKind.RELEASE.value: {},
            ProviderEntityKind.TRACK.value: {},
        }
        for provider_name, search_result in provider_results.items():
            for hit in search_result.items:
                grouped_results[hit.kind.value].setdefault(provider_name, []).append(hit.entity)

        results: list[SearchResultItemPayload] = []
        for kind_name in [ProviderEntityKind.ARTIST.value, ProviderEntityKind.RELEASE.value, ProviderEntityKind.TRACK.value]:
            provider_items = grouped_results[kind_name]
            if not provider_items:
                continue
            results.extend(self._merge_kind_results(kind_name, provider_items))

        decision_order = {
            MatchDecision.AUTO: 0,
            MatchDecision.AMBIGUOUS: 1,
            MatchDecision.REJECT: 2,
        }
        return sorted(
            results,
            key=lambda item: (decision_order.get(item.decision, 9), -item.score, item.kind),
        )

    def _merge_kind_results(
        self,
        kind_name: str,
        provider_items: dict[str, list[ProviderEntity]],
    ) -> list[SearchResultItemPayload]:
        left_items = list(provider_items.get("youtube", []))
        right_items = list(provider_items.get("yandex", []))
        used_right_ids: set[str] = set()
        merged_results: list[SearchResultItemPayload] = []

        for left in left_items:
            available_right = [candidate for candidate in right_items if candidate.provider_id not in used_right_ids]
            if kind_name == ProviderEntityKind.ARTIST.value:
                match_result = self.matching_service.match_artists(left, available_right)  # type: ignore[arg-type]
            elif kind_name == ProviderEntityKind.RELEASE.value:
                match_result = self.matching_service.match_releases(left, available_right)  # type: ignore[arg-type]
            else:
                match_result = self.matching_service.match_tracks(left, available_right)  # type: ignore[arg-type]

            matched_right = None
            canonical_id = None
            if match_result.matched_candidate is not None:
                matched_right = next(
                    (candidate for candidate in available_right if candidate.provider_id == match_result.matched_candidate.provider_id),
                    None,
                )
            if matched_right is not None and match_result.decision != MatchDecision.REJECT:
                used_right_ids.add(matched_right.provider_id)
                canonical_id = self.link_service.persist_match(
                    left,
                    matched_right,
                    decision=match_result.decision,
                    score=match_result.score,
                    features_json=match_result.features_json,
                )
            else:
                self.link_service.persist_platform_entity(left)

            merged_results.append(
                SearchResultItemPayload(
                    kind=kind_name,
                    canonical_id=canonical_id,
                    decision=match_result.decision,
                    score=match_result.score,
                    features_json=match_result.features_json,
                    platforms={
                        "youtube": self._to_platform_payload(left) if left.provider.value == "youtube" else self._to_platform_payload(matched_right),
                        "yandex": self._to_platform_payload(matched_right) if matched_right else None,
                    },
                )
            )

        for right in right_items:
            if right.provider_id in used_right_ids:
                continue
            self.link_service.persist_platform_entity(right)
            merged_results.append(
                SearchResultItemPayload(
                    kind=kind_name,
                    canonical_id=None,
                    decision=MatchDecision.REJECT,
                    score=0.0,
                    features_json={"entity_kind": kind_name, "reason": "unmatched_provider_result"},
                    platforms={
                        "youtube": None,
                        "yandex": self._to_platform_payload(right),
                    },
                )
            )

        return merged_results

    def _to_platform_payload(self, entity: Optional[ProviderEntity]) -> Optional[SearchPlatformEntityPayload]:
        if entity is None:
            return None

        if isinstance(entity, ProviderArtist):
            return SearchPlatformEntityPayload(
                provider=entity.provider.value,
                provider_id=entity.provider_id,
                kind=entity.kind.value,
                label=entity.name,
                display_norm=entity.display_norm,
                match_norm=entity.match_norm,
                url=entity.url,
            )
        if isinstance(entity, ProviderRelease):
            return SearchPlatformEntityPayload(
                provider=entity.provider.value,
                provider_id=entity.provider_id,
                kind=entity.kind.value,
                label=entity.title,
                display_norm=entity.display_norm,
                match_norm=entity.match_norm,
                url=entity.url,
                artist_names=entity.artist_names,
                release_year=entity.release_year,
                release_type=entity.release_type,
                track_count=entity.track_count,
                version_tags_json=entity.version_tags_json,
            )
        return SearchPlatformEntityPayload(
            provider=entity.provider.value,
            provider_id=entity.provider_id,
            kind=entity.kind.value,
            label=entity.title,
            display_norm=entity.display_norm,
            match_norm=entity.match_norm,
            url=entity.url,
            artist_names=entity.artist_names,
            duration_ms=entity.duration_ms,
            version_tags_json=entity.version_tags_json,
        )

    def _normalize_limit(self, limit: Optional[int]) -> int:
        if limit is None:
            return self.settings.search_default_limit
        return max(1, min(limit, self.settings.search_max_limit))

    def _build_cache_key(self, *, normalized_query: str, kind: Optional[str], limit: int) -> str:
        return f"search:v1:{kind or 'all'}:{limit}:{normalized_query}"

    def _is_stale(self, cache_entry, now: datetime) -> bool:
        stale_at = self._coerce_aware(cache_entry.stale_at)
        return stale_at is not None and stale_at <= now

    def _is_expired(self, cache_entry, now: datetime) -> bool:
        expires_at = self._coerce_aware(cache_entry.expires_at)
        return expires_at is not None and expires_at <= now

    def _response_from_cache(
        self,
        response_json: dict[str, Any],
        *,
        cache_status: str,
        hit_count: int,
        last_refreshed_at: Optional[datetime],
        stale_at: Optional[datetime],
        expires_at: Optional[datetime],
        refresh_queued: bool,
        refresh_job_id: Optional[str],
    ) -> SearchResponse:
        response = SearchResponse.model_validate(
            {
                **response_json,
                "cache": {
                    "status": cache_status,
                    "hit_count": hit_count,
                    "last_refreshed_at": self._coerce_aware(last_refreshed_at),
                    "stale_at": self._coerce_aware(stale_at),
                    "expires_at": self._coerce_aware(expires_at),
                    "refresh_queued": refresh_queued,
                    "refresh_job_id": refresh_job_id,
                },
            }
        )
        return response

    def _coerce_aware(self, value: Optional[datetime]) -> Optional[datetime]:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def _has_providers(self) -> bool:
        return bool(self.provider_registry.all())
