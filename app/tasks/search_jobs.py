from __future__ import annotations

from typing import Optional


def refresh_search_cache(
    query: str,
    *,
    kind: Optional[str] = None,
    limit: Optional[int] = None,
) -> None:
    raise NotImplementedError("Search cache refresh worker is not implemented yet")
