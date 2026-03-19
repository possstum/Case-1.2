from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import (
    enforce_search_rate_limit,
    enforce_sync_rate_limit,
    get_artist_service,
    get_release_service,
    get_web_search_service,
    get_sync_service,
    get_track_service,
)
from app.core.errors import ServiceUnavailableError
from app.services.artist_service import ArtistService
from app.services.release_service import ReleaseService
from app.services.search_service import SearchService
from app.services.sync_service import SyncService
from app.services.track_service import TrackService
from app.web.presenters import build_search_page_view, requested_kinds_for_tab, resolve_search_tab
from app.web.render import (
    render_artist_page,
    render_job_page,
    render_release_page,
    render_search_page,
    render_track_page,
)

web_router = APIRouter(include_in_schema=False)
UiSearchKind = Literal["", "artist", "release", "track"]
UiSearchTab = Literal["all", "artist", "release", "track", "missing"]


@web_router.get("/", response_class=RedirectResponse)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/ui", status_code=status.HTTP_302_FOUND)


@web_router.get("/ui", response_class=HTMLResponse, dependencies=[Depends(enforce_search_rate_limit)])
def ui_search(
    q: Optional[str] = Query(default=None, min_length=1),
    tab: Optional[UiSearchTab] = Query(default=None),
    kind: Optional[UiSearchKind] = Query(default=None),
    limit: Optional[int] = Query(default=None, ge=1),
    search_service: SearchService = Depends(get_web_search_service),
) -> HTMLResponse:
    normalized_kind = kind or None
    active_tab = resolve_search_tab(tab, normalized_kind)
    responses_by_kind = {}
    notice = None
    if q:
        try:
            for requested_kind in requested_kinds_for_tab(active_tab):
                responses_by_kind[requested_kind] = search_service.search(query=q, kind=requested_kind, limit=limit)
        except ServiceUnavailableError:
            notice = "Поиск сейчас недоступен: live providers не настроены или временно выключены."
    page = build_search_page_view(
        query=q or "",
        active_tab=active_tab,
        limit=limit,
        responses_by_kind=responses_by_kind,
        provider_notice=notice,
    )
    return HTMLResponse(
        render_search_page(
            page=page,
            limit=limit,
        )
    )


@web_router.get("/ui/artists/{artist_id}", response_class=HTMLResponse)
def ui_artist(
    artist_id: int,
    artist_service: ArtistService = Depends(get_artist_service),
) -> HTMLResponse:
    return HTMLResponse(render_artist_page(artist_service.get_artist(artist_id)))


@web_router.get("/ui/releases/{release_id}", response_class=HTMLResponse)
def ui_release(
    release_id: int,
    release_service: ReleaseService = Depends(get_release_service),
) -> HTMLResponse:
    return HTMLResponse(render_release_page(release_service.get_release(release_id)))


@web_router.get("/ui/tracks/{track_id}", response_class=HTMLResponse)
def ui_track(
    track_id: int,
    track_service: TrackService = Depends(get_track_service),
) -> HTMLResponse:
    return HTMLResponse(render_track_page(track_service.get_track(track_id)))


@web_router.post(
    "/ui/sync/{kind}/{target_id}",
    response_class=RedirectResponse,
    dependencies=[Depends(enforce_sync_rate_limit)],
)
def ui_sync(
    kind: str,
    target_id: int,
    sync_service: SyncService = Depends(get_sync_service),
) -> RedirectResponse:
    response = sync_service.enqueue(kind=kind, target_id=target_id)
    return RedirectResponse(url=f"/ui/jobs/{response.job.id}", status_code=status.HTTP_303_SEE_OTHER)


@web_router.get("/ui/jobs/{job_id}", response_class=HTMLResponse)
def ui_job(
    job_id: str,
    sync_service: SyncService = Depends(get_sync_service),
) -> HTMLResponse:
    return HTMLResponse(render_job_page(sync_service.get_job(job_id)))
