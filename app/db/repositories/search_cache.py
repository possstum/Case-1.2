from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import SearchCache


class SearchCacheRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_key(self, cache_key: str) -> Optional[SearchCache]:
        statement = select(SearchCache).where(SearchCache.cache_key == cache_key)
        return self.session.scalar(statement)

    def upsert(
        self,
        *,
        cache_key: str,
        query_text: str,
        normalized_query: str,
        kind: Optional[str],
        response_json: dict[str, Any],
        is_partial: bool,
        stale_at: Optional[datetime],
        expires_at: Optional[datetime],
        last_refreshed_at: Optional[datetime] = None,
    ) -> SearchCache:
        cache_entry = self.get_by_key(cache_key)
        if cache_entry is None:
            cache_entry = SearchCache(
                cache_key=cache_key,
                query_text=query_text,
                normalized_query=normalized_query,
                kind=kind,
                response_json=response_json,
                is_partial=is_partial,
                stale_at=stale_at,
                expires_at=expires_at,
                last_refreshed_at=last_refreshed_at or datetime.now(timezone.utc),
            )
            self.session.add(cache_entry)
        else:
            cache_entry.query_text = query_text
            cache_entry.normalized_query = normalized_query
            cache_entry.kind = kind
            cache_entry.response_json = response_json
            cache_entry.is_partial = is_partial
            cache_entry.stale_at = stale_at
            cache_entry.expires_at = expires_at
            cache_entry.last_refreshed_at = last_refreshed_at or datetime.now(timezone.utc)

        self.session.flush()
        return cache_entry

    def mark_hit(self, cache_entry: SearchCache) -> SearchCache:
        cache_entry.hit_count += 1
        self.session.flush()
        return cache_entry
