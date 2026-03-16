from __future__ import annotations

import json
from html import escape
from typing import Optional

from app.api.schemas.entities import (
    ArtistDetailResponse,
    LinkedPlatformEntityPayload,
    ReleaseDetailResponse,
    TrackDetailResponse,
)
from app.api.schemas.jobs import SyncJobResponse
from app.api.schemas.search import SearchPlatformEntityPayload, SearchResponse, SearchResultItemPayload


def render_search_page(
    *,
    query: str = "",
    kind: Optional[str] = None,
    limit: Optional[int] = None,
    response: Optional[SearchResponse] = None,
    notice: Optional[str] = None,
) -> str:
    body = [
        "<section class='hero'>",
        "<p class='eyebrow'>NETvRF MVP</p>",
        "<h1>Cross-platform matching without pretending certainty.</h1>",
        "<p class='lede'>Search cached matches between YouTube Music and Yandex Music, inspect explainability, and sync linked entities on demand.</p>",
        "</section>",
        "<section class='panel'>",
        "<form class='search-form' method='get' action='/ui'>",
        f"<label><span>Query</span><input type='text' name='q' value='{escape(query)}' placeholder='Krovostok' required></label>",
        "<label><span>Kind</span><select name='kind'>",
        _option("", "Any", kind),
        _option("artist", "Artist", kind),
        _option("release", "Release", kind),
        _option("track", "Track", kind),
        "</select></label>",
        f"<label><span>Limit</span><input type='number' name='limit' min='1' max='25' value='{limit or 10}'></label>",
        "<button type='submit'>Search</button>",
        "</form>",
        "</section>",
    ]

    if notice:
        body.extend(
            [
                "<section class='panel'>",
                f"<p class='muted'>{escape(notice)}</p>",
                "</section>",
            ]
        )

    if response is not None:
        body.extend(
            [
                "<section class='panel'>",
                "<div class='row between wrap'>",
                f"<h2>Results for <code>{escape(response.query)}</code></h2>",
                f"<div class='row wrap'>{_badge(response.cache.status, response.cache.status)}{_badge('partial' if response.partial else 'complete', 'partial' if response.partial else 'auto')}</div>",
                "</div>",
                f"<p class='muted'>Cache: {escape(response.cache.status)}. Missing platforms: {escape(', '.join(response.missing_platforms) if response.missing_platforms else 'none')}.</p>",
            ]
        )
        if response.results:
            body.append("<div class='stack'>")
            for item in response.results:
                body.append(_render_search_item(item))
            body.append("</div>")
        else:
            body.append("<p class='empty'>No merged results yet. If providers are not implemented, the page will stay partial rather than guess.</p>")
        body.append("</section>")
    else:
        body.extend(
            [
                "<section class='panel'>",
                "<p class='muted'>Search is cache-first. Ambiguous states stay visible in both API and UI.</p>",
                "</section>",
            ]
        )

    return _render_layout(title="Search", content="".join(body))


def render_artist_page(detail: ArtistDetailResponse) -> str:
    content = [
        _render_entity_header(
            title=detail.display_name,
            kind=detail.kind,
            entity_id=detail.id,
            partial=detail.partial,
            missing_platforms=detail.missing_platforms,
        ),
        "<section class='panel'><h2>Aliases</h2>",
    ]
    if detail.aliases:
        content.append("<ul class='simple-list'>")
        for alias in detail.aliases:
            content.append(f"<li>{escape(alias.alias)} <span class='muted'>[{escape(alias.match_norm)}]</span></li>")
        content.append("</ul>")
    else:
        content.append("<p class='empty'>No aliases stored.</p>")
    content.append("</section>")
    content.append(_render_platforms(detail.platforms))
    content.append("<section class='panel'><h2>Related releases</h2>")
    content.append(_render_release_links(detail.releases))
    content.append("</section>")
    content.append("<section class='panel'><h2>Related tracks</h2>")
    content.append(_render_track_links(detail.tracks))
    content.append("</section>")
    return _render_layout(title=detail.display_name, content="".join(content))


def render_release_page(detail: ReleaseDetailResponse) -> str:
    content = [
        _render_entity_header(
            title=detail.title,
            kind=detail.kind,
            entity_id=detail.id,
            partial=detail.partial,
            missing_platforms=detail.missing_platforms,
        ),
        "<section class='panel'><h2>Credits</h2>",
    ]
    if detail.artists:
        content.append("<ul class='simple-list'>")
        for artist in detail.artists:
            content.append(
                f"<li><a href='/ui/artists/{artist.artist_id}'>{escape(artist.display_name)}</a> <span class='muted'>{escape(artist.role)} #{artist.position}</span></li>"
            )
        content.append("</ul>")
    else:
        content.append("<p class='empty'>No artist credits stored.</p>")
    content.append("</section>")
    content.append(_render_platforms(detail.platforms))
    content.append("<section class='panel'><h2>Tracklist</h2>")
    content.append(_render_track_links(detail.tracks))
    content.append("</section>")
    return _render_layout(title=detail.title, content="".join(content))


def render_track_page(detail: TrackDetailResponse) -> str:
    content = [
        _render_entity_header(
            title=detail.title,
            kind=detail.kind,
            entity_id=detail.id,
            partial=detail.partial,
            missing_platforms=detail.missing_platforms,
        ),
        "<section class='panel'><h2>Credits</h2>",
    ]
    if detail.artists:
        content.append("<ul class='simple-list'>")
        for artist in detail.artists:
            content.append(
                f"<li><a href='/ui/artists/{artist.artist_id}'>{escape(artist.display_name)}</a> <span class='muted'>{escape(artist.role)} #{artist.position}</span></li>"
            )
        content.append("</ul>")
    else:
        content.append("<p class='empty'>No artist credits stored.</p>")
    content.append("</section>")
    content.append(_render_platforms(detail.platforms))
    content.append("<section class='panel'><h2>Related releases</h2>")
    content.append(_render_release_links(detail.releases))
    content.append("</section>")
    return _render_layout(title=detail.title, content="".join(content))


def render_job_page(job: SyncJobResponse) -> str:
    title = f"Sync job {job.id}"
    refresh_seconds = 3 if job.status in {"queued", "started"} else None
    body = [
        "<section class='panel'>",
        f"<p class='eyebrow'>Sync Job</p><h1>{escape(job.kind)} #{escape(job.target_id)}</h1>",
        f"<div class='row wrap'>{_badge(job.status, job.status)}</div>",
        f"<p class='muted'>Attempts: {job.attempts}. Queue: {escape(job.queue_name)}.</p>",
        "<div class='row wrap'>",
        f"<a class='button secondary' href='/ui/{escape(job.kind)}s/{escape(job.target_id)}'>Back to entity</a>",
        f"<a class='button ghost' href='/jobs/{escape(job.id)}'>JSON</a>",
        "</div>",
        "</section>",
    ]
    if job.result_json:
        body.append("<section class='panel'><h2>Result</h2>")
        body.append(_render_json(job.result_json))
        body.append("</section>")
    if job.error_json:
        body.append("<section class='panel'><h2>Error</h2>")
        body.append(_render_json(job.error_json))
        body.append("</section>")
    return _render_layout(
        title=title,
        content="".join(body),
        refresh_seconds=refresh_seconds,
        body_attrs={"data-auto-refresh-seconds": str(refresh_seconds or "")},
    )


def _render_search_item(item: SearchResultItemPayload) -> str:
    title = f"{item.kind} · {item.decision}"
    href = f"/ui/{item.kind}s/{item.canonical_id}" if item.canonical_id is not None else ""
    body = [
        "<article class='result-card'>",
        "<div class='row between wrap'>",
        f"<h3>{escape(title)}</h3>",
        f"<div class='row wrap'>{_badge(item.decision, item.decision)}<span class='score'>score {item.score:.2f}</span></div>",
        "</div>",
    ]
    if href:
        body.append(f"<p><a href='{href}'>Open canonical entity #{item.canonical_id}</a></p>")
    else:
        body.append("<p class='empty'>No canonical entity was created for this result.</p>")
    body.append("<div class='platform-grid'>")
    for provider_name in ("youtube", "yandex"):
        body.append(_render_platform_card(item.platforms.get(provider_name), provider_name))
    body.append("</div>")
    body.append("<h4>Explainability</h4>")
    body.append("<p class='muted'>features_json</p>")
    body.append(_render_json(item.features_json))
    body.append("</article>")
    return "".join(body)


def _render_entity_header(*, title: str, kind: str, entity_id: int, partial: bool, missing_platforms: list[str]) -> str:
    return "".join(
        [
            "<section class='panel'>",
            f"<p class='eyebrow'>{escape(kind)}</p>",
            f"<div class='row between wrap'><h1>{escape(title)}</h1><div class='row wrap'>{_badge('partial' if partial else 'complete', 'partial' if partial else 'auto')}</div></div>",
            f"<p class='muted'>Canonical id: {entity_id}. Missing platforms: {escape(', '.join(missing_platforms) if missing_platforms else 'none')}.</p>",
            "<div class='row wrap'>",
            f"<a class='button secondary' href='/{escape(kind)}s/{entity_id}'>JSON</a>",
            f"<form method='post' action='/ui/sync/{escape(kind)}/{entity_id}'><button type='submit'>Enqueue sync</button></form>",
            "</div>",
            "</section>",
        ]
    )


def _render_platforms(platforms: dict[str, Optional[LinkedPlatformEntityPayload]]) -> str:
    body = ["<section class='panel'><h2>Platform links</h2><div class='platform-grid'>"]
    for provider_name in ("youtube", "yandex"):
        body.append(_render_platform_card(platforms.get(provider_name), provider_name))
    body.append("</div></section>")
    return "".join(body)


def _render_platform_card(
    payload: Optional[LinkedPlatformEntityPayload | SearchPlatformEntityPayload],
    provider_name: str,
) -> str:
    if payload is None:
        return "".join(
            [
                "<article class='platform-card empty-card'>",
                f"<h4>{escape(provider_name)}</h4>",
                "<p class='empty'>Missing link</p>",
                "</article>",
            ]
        )

    rows = [
        "<article class='platform-card'>",
        f"<div class='row between wrap'><h4>{escape(payload.provider)}</h4>{_render_platform_badges(payload)}</div>",
        f"<p><strong>{escape(payload.label)}</strong></p>",
        f"<p class='muted'>provider_id: {escape(payload.provider_id)}</p>",
    ]
    explainability = getattr(payload, "explainability", None)
    if explainability is not None:
        rows.append(f"<p class='muted'>score: {explainability.score:.2f}</p>")
    if payload.artist_names:
        rows.append(f"<p class='muted'>artists: {escape(', '.join(payload.artist_names))}</p>")
    if payload.url:
        rows.append(f"<p><a href='{escape(payload.url)}' target='_blank' rel='noreferrer'>Open provider page</a></p>")
    if explainability is not None:
        rows.append("<details><summary>features_json</summary>")
        rows.append(_render_json(explainability.features_json))
        rows.append("</details>")
    rows.append("</article>")
    return "".join(rows)


def _render_platform_badges(payload: LinkedPlatformEntityPayload | SearchPlatformEntityPayload) -> str:
    explainability = getattr(payload, "explainability", None)
    if explainability is None:
        return ""
    return _badge(explainability.decision, explainability.decision)


def _render_release_links(releases) -> str:
    if not releases:
        return "<p class='empty'>No releases linked.</p>"
    body = ["<ul class='simple-list'>"]
    for release in releases:
        subtitle = []
        if release.release_year is not None:
            subtitle.append(str(release.release_year))
        if release.release_type:
            subtitle.append(release.release_type)
        if release.role:
            subtitle.append(release.role)
        if release.track_number is not None:
            subtitle.append(f"track {release.track_number}")
        body.append(
            f"<li><a href='/ui/releases/{release.release_id}'>{escape(release.title)}</a> <span class='muted'>{escape(' · '.join(subtitle))}</span></li>"
        )
    body.append("</ul>")
    return "".join(body)


def _render_track_links(tracks) -> str:
    if not tracks:
        return "<p class='empty'>No tracks linked.</p>"
    body = ["<ul class='simple-list'>"]
    for track in tracks:
        subtitle = []
        if track.duration_ms is not None:
            subtitle.append(f"{track.duration_ms} ms")
        if track.role:
            subtitle.append(track.role)
        if track.track_number is not None:
            subtitle.append(f"#{track.track_number}")
        body.append(
            f"<li><a href='/ui/tracks/{track.track_id}'>{escape(track.title)}</a> <span class='muted'>{escape(' · '.join(subtitle))}</span></li>"
        )
    body.append("</ul>")
    return "".join(body)


def _render_json(payload: object) -> str:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    return f"<pre>{escape(rendered)}</pre>"


def _option(value: str, label: str, selected: Optional[str]) -> str:
    selected_attr = " selected" if value == (selected or "") else ""
    return f"<option value='{escape(value)}'{selected_attr}>{escape(label)}</option>"


def _badge(label: str, tone: str) -> str:
    safe_tone = escape(tone.replace("_", "-"))
    return f"<span class='badge badge-{safe_tone}'>{escape(label)}</span>"


def _render_layout(
    *,
    title: str,
    content: str,
    refresh_seconds: Optional[int] = None,
    body_attrs: Optional[dict[str, str]] = None,
) -> str:
    refresh_tag = (
        f"<meta http-equiv='refresh' content='{refresh_seconds}'>"
        if refresh_seconds is not None
        else ""
    )
    attrs = " ".join(
        f"{escape(key)}='{escape(value)}'"
        for key, value in (body_attrs or {}).items()
        if value
    )
    return "".join(
        [
            "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
            "<meta name='viewport' content='width=device-width, initial-scale=1'>",
            f"<title>{escape(title)} · NETvRF</title>",
            refresh_tag,
            "<link rel='stylesheet' href='/static/app.css'>",
            "<script defer src='/static/app.js'></script>",
            "</head>",
            f"<body {attrs}>",
            "<header class='site-header'><a class='brand' href='/ui'>NETvRF</a><nav><a href='/ui'>Search</a><a href='/health'>Health</a></nav></header>",
            "<main class='shell'>",
            content,
            "</main></body></html>",
        ]
    )
