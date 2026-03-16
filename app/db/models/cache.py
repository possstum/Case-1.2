from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixins import TimestampMixin, utcnow


class SearchCache(TimestampMixin, Base):
    __tablename__ = "search_cache"
    __table_args__ = (
        Index("ix_search_cache_normalized_query_kind", "normalized_query", "kind"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cache_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    query_text: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_query: Mapped[str] = mapped_column(String(512), nullable=False)
    kind: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    response_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    is_partial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.current_timestamp(),
    )
    stale_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

