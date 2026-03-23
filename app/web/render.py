from __future__ import annotations

from html import escape
from typing import Optional

from app.api.schemas.entities import (
    ArtistDetailResponse,
    LinkedPlatformEntityPayload,
    MissingOnYandexViewPayload,
    ProviderCatalogSectionPayload,
    ReleaseDetailResponse,
    TrackDetailResponse,
)
from app.api.schemas.jobs import SyncJobResponse
from app.api.schemas.search import SearchPlatformEntityPayload
from app.web.presenters import ActionView, BadgeView, SearchCardView, SearchPageView, SearchSectionView

ENTITY_KIND_LABELS = {
    "artist": "Исполнитель",
    "release": "Релиз",
    "track": "Трек",
}


def render_search_page(*, page: SearchPageView, limit: Optional[int] = None) -> str:
    body = [
        "<section class='panel search-shell-panel'>",
        "<div class='search-shell-head'>",
        "<div>",
        "<p class='eyebrow'>NETvRF</p>",
        "<h1>Поиск музыки без лишнего шума</h1>",
        "<p class='lede'>Ищите исполнителей, альбомы и треки, быстро видьте доступность на Yandex и YouTube и отдельно проверяйте сценарий «Нет в РФ».</p>",
        "</div>",
        "</div>",
        "<form class='search-form search-form-compact' method='get' action='/ui' data-ui-search-form='true'>",
        f"<input type='hidden' name='tab' value='{escape(page.active_tab)}'>",
        _hidden_limit(limit),
        "<label class='search-query-field'>",
        "<span class='sr-only'>Поисковый запрос</span>",
        f"<input type='text' name='q' value='{escape(page.query)}' placeholder='Маваши, Motorama, Кровосток' required>",
        "</label>",
        "<button type='submit'>Найти</button>",
        "</form>",
        "<nav class='search-tabs' aria-label='Тип результатов'>",
    ]
    for tab in page.tabs:
        tab_class = "search-tab active" if tab.active else "search-tab"
        body.append(f"<a class='{tab_class}' href='{escape(tab.href)}'>{escape(tab.label)}</a>")
    body.append("</nav></section>")

    for notice in page.notices:
        body.append(_render_notice(notice.text, notice.tone))

    if not page.query:
        body.append("<section class='panel intro-panel'>")
        body.append(f"<h2>{escape(page.empty_title)}</h2>")
        body.append(f"<p class='muted'>{escape(page.empty_text)}</p>")
        body.append("</section>")
        return _render_layout(title="Поиск", content="".join(body))

    if page.featured_artist is not None:
        body.append(_render_featured_artist(page.featured_artist))

    has_section_items = any(section.items for section in page.sections)
    if has_section_items or page.active_tab != "all":
        for section in page.sections:
            body.append(_render_search_section(section))
    else:
        body.append("<section class='panel empty-state'>")
        body.append(f"<h2>{escape(page.empty_title)}</h2>")
        body.append(f"<p class='muted'>{escape(page.empty_text)}</p>")
        body.append("</section>")

    return _render_layout(title="Поиск", content="".join(body))


def render_artist_page(detail: ArtistDetailResponse) -> str:
    album_releases = [release for release in detail.releases if _is_album_release_type(release.release_type)]
    has_extended_content = bool(
        detail.aliases
        or detail.releases
        or detail.tracks
        or detail.yandex_catalog_sections
        or detail.missing_on_yandex_view.total_items
    )
    content = [
        _render_entity_hero(
            title=detail.display_name,
            kind=detail.kind,
            entity_id=detail.id,
            platforms=detail.platforms,
        ),
        _render_platforms(detail.platforms),
    ]
    if has_extended_content:
        content.extend(
            [
                _render_artist_stats(
                    release_count=len(detail.releases),
                    album_count=len(album_releases),
                    missing_on_yandex_count=detail.missing_on_yandex_view.total_items,
                ),
                _render_yandex_catalog_sections(detail.yandex_catalog_sections),
                "<section class='panel'><h2>Релизы</h2>",
                _render_release_cards(detail.releases, empty_message="Связанные релизы пока не сохранены."),
                "</section>",
                "<section class='panel'><h2>Нет на Yandex</h2>",
                _render_missing_on_yandex_view(detail.missing_on_yandex_view),
                "</section>",
                "<section class='panel'><h2>Треки</h2>",
                _render_track_links(detail.tracks),
                "</section>",
                "<section class='panel'><h2>Варианты названия</h2>",
            ]
        )
        if detail.aliases:
            content.append("<ul class='simple-list'>")
            for alias in detail.aliases:
                content.append(f"<li>{escape(alias.alias)} <span class='muted'>[{escape(alias.match_norm)}]</span></li>")
            content.append("</ul>")
        else:
            content.append("<p class='empty'>Сохраненных вариантов названия пока нет.</p>")
        content.append("</section>")
    return _render_layout(title=detail.display_name, content="".join(content))


def render_release_page(detail: ReleaseDetailResponse) -> str:
    content = [
        _render_entity_hero(
            title=detail.title,
            kind=detail.kind,
            entity_id=detail.id,
            platforms=detail.platforms,
            meta=_release_meta(detail.release_year, detail.release_type, None),
        ),
        _render_entity_fill_state(
            kind=detail.kind,
            entity_id=detail.id,
            title=detail.title,
            has_related_content=bool(detail.artists or detail.tracks),
        ),
        _render_platforms(detail.platforms),
        "<section class='panel'><h2>Исполнители</h2>",
    ]
    if detail.artists:
        content.append("<ul class='simple-list'>")
        for artist in detail.artists:
            content.append(
                f"<li><a href='/ui/artists/{artist.artist_id}'>{escape(artist.display_name)}</a> <span class='muted'>{escape(artist.role)} #{artist.position}</span></li>"
            )
        content.append("</ul>")
    else:
        content.append("<p class='empty'>Исполнители для этого релиза пока не сохранены.</p>")
    content.append("</section>")
    content.append("<section class='panel'><h2>Треклист</h2>")
    content.append(_render_track_links(detail.tracks))
    content.append("</section>")
    return _render_layout(title=detail.title, content="".join(content))


def render_track_page(detail: TrackDetailResponse) -> str:
    content = [
        _render_entity_hero(
            title=detail.title,
            kind=detail.kind,
            entity_id=detail.id,
            platforms=detail.platforms,
            meta=_format_duration_ms(detail.duration_ms) if detail.duration_ms is not None else None,
        ),
        _render_entity_fill_state(
            kind=detail.kind,
            entity_id=detail.id,
            title=detail.title,
            has_related_content=bool(detail.artists or detail.releases),
        ),
        _render_platforms(detail.platforms),
        "<section class='panel'><h2>Исполнители</h2>",
    ]
    if detail.artists:
        content.append("<ul class='simple-list'>")
        for artist in detail.artists:
            content.append(
                f"<li><a href='/ui/artists/{artist.artist_id}'>{escape(artist.display_name)}</a> <span class='muted'>{escape(artist.role)} #{artist.position}</span></li>"
            )
        content.append("</ul>")
    else:
        content.append("<p class='empty'>Исполнители для этого трека пока не сохранены.</p>")
    content.append("</section>")
    content.append("<section class='panel'><h2>Релизы</h2>")
    content.append(_render_release_links(detail.releases))
    content.append("</section>")
    return _render_layout(title=detail.title, content="".join(content))


def render_job_page(job: SyncJobResponse) -> str:
    title = "Обновление карточки"
    refresh_seconds = 3 if job.status in {"queued", "started"} else None
    status_copy = {
        "queued": "Поставили обновление в очередь.",
        "started": "Карточка обновляется прямо сейчас.",
        "finished": "Карточка обновлена.",
        "failed": "Пока не получилось обновить карточку.",
    }.get(job.status, "Статус обновления изменился.")
    body = [
        "<section class='panel'>",
        f"<p class='eyebrow'>Обновление</p><h1>{escape(job.kind.title())}</h1>",
        f"<div class='badge-row'>{_badge(job.status, job.status)}</div>",
        f"<p class='muted'>{escape(status_copy)}</p>",
        "<div class='action-row'>",
        f"<a class='button secondary' href='/ui/{escape(job.kind)}s/{escape(job.target_id)}'>Вернуться к сущности</a>",
        "</div>",
        "</section>",
    ]
    return _render_layout(
        title=title,
        content="".join(body),
        refresh_seconds=refresh_seconds,
        body_attrs={"data-auto-refresh-seconds": str(refresh_seconds or "")},
    )


def _render_featured_artist(card: SearchCardView) -> str:
    body = [
        "<section class='panel featured-card' data-featured-artist='true'>",
        "<p class='eyebrow'>Лучшее совпадение по исполнителю</p>",
        _render_card_header(card, heading_level="h2"),
    ]
    if card.note:
        body.append(f"<p class='muted'>{escape(card.note)}</p>")
    body.append(_render_card_actions(card))
    body.append("</section>")
    return "".join(body)


def _render_search_section(section: SearchSectionView) -> str:
    body = [f"<section class='panel search-section' data-section='{escape(section.key)}'>"]
    body.append(f"<div class='section-head'><h2>{escape(section.title)}</h2>")
    if section.description:
        body.append(f"<p class='muted'>{escape(section.description)}</p>")
    body.append("</div>")
    if section.items:
        body.append("<div class='card-list'>")
        for card in section.items:
            body.append(_render_search_card(card))
        body.append("</div>")
    else:
        body.append(f"<p class='empty'>{escape(section.empty_message)}</p>")
    body.append("</section>")
    return "".join(body)


def _render_search_card(card: SearchCardView) -> str:
    body = [f"<article class='result-card' data-kind='{escape(card.kind)}'>"]
    body.append(_render_card_header(card))
    if card.note:
        body.append(f"<p class='muted'>{escape(card.note)}</p>")
    body.append(_render_card_actions(card))
    body.append("</article>")
    return "".join(body)


def _render_card_header(card: SearchCardView, *, heading_level: str = "h3") -> str:
    title_html = escape(card.title)
    if card.primary_action is not None and not card.primary_action.external:
        title_html = f"<a href='{escape(card.primary_action.href)}'>{title_html}</a>"

    body = [
        "<div class='card-head'>",
        "<div class='card-copy'>",
        f"<{heading_level}>{title_html}</{heading_level}>",
        f"<p>{escape(card.subtitle)}</p>",
    ]
    if card.meta:
        body.append(f"<p class='meta-line'>{escape(card.meta)}</p>")
    body.append("</div>")
    body.append("<div class='badge-row'>")
    for badge in card.badges:
        body.append(_render_badge_view(badge))
    body.append("</div></div>")
    return "".join(body)


def _render_card_actions(card: SearchCardView) -> str:
    actions: list[str] = []
    if card.primary_action is not None:
        actions.append(_render_action(card.primary_action))
    for action in card.provider_actions:
        actions.append(_render_action(action))
    if not actions:
        return ""
    return f"<div class='action-row'>{''.join(actions)}</div>"


def _render_entity_hero(
    *,
    title: str,
    kind: str,
    entity_id: int,
    platforms: dict[str, Optional[LinkedPlatformEntityPayload]],
    meta: Optional[str] = None,
) -> str:
    summary = _entity_platform_summary(platforms)
    badges = _entity_availability_badges(platforms)
    body = [
        "<section class='panel availability-hero'>",
        f"<p class='eyebrow'>{escape(ENTITY_KIND_LABELS.get(kind, kind))}</p>",
        "<div class='availability-hero-head'>",
        "<div>",
        f"<h1>{escape(title)}</h1>",
        f"<p class='lede'>{escape(summary)}</p>",
    ]
    if meta:
        body.append(f"<p class='muted'>{escape(meta)}</p>")
    body.append("</div>")
    body.append("<div class='badge-row'>")
    for badge in badges:
        body.append(_render_badge_view(badge))
    body.append("</div></div></section>")
    return "".join(body)


def _render_entity_fill_state(*, kind: str, entity_id: int, title: str, has_related_content: bool) -> str:
    if has_related_content:
        return ""
    label = ENTITY_KIND_LABELS.get(kind, kind)
    return "".join(
        [
            "<section class='panel empty-fill-panel'>",
            f"<h2>Карточка «{escape(title)}» ещё наполняется</h2>",
            f"<p class='muted'>Мы уже подтвердили {escape(label.lower())} на платформах, но подробные релизы, треки и связи для этой карточки ещё не подгружены.</p>",
            "<div class='action-row'>",
            f"<form method='post' action='/ui/sync/{escape(kind)}/{entity_id}'><button type='submit'>Обновить карточку</button></form>",
            f"<a class='button secondary' href='/ui'>Вернуться к поиску</a>",
            "</div>",
            "</section>",
        ]
    )


def _render_platforms(platforms: dict[str, Optional[LinkedPlatformEntityPayload]]) -> str:
    body = [
        "<section class='panel'>",
        "<div class='section-head'><h2>Где доступно</h2><p class='muted'>Подтвержденные карточки по платформам и быстрые переходы.</p></div>",
        "<div class='platform-grid'>",
    ]
    for provider_name in ("yandex", "youtube"):
        body.append(_render_platform_card(platforms.get(provider_name), provider_name))
    body.append("</div></section>")
    return "".join(body)


def _render_platform_card(
    payload: Optional[LinkedPlatformEntityPayload | SearchPlatformEntityPayload],
    provider_name: str,
) -> str:
    label = "Yandex" if provider_name == "yandex" else "YouTube"
    if payload is None:
        return "".join(
            [
                "<article class='platform-card empty-card'>",
                f"<h3>{label}</h3>",
                f"<p class='empty'>Подтвержденной карточки на {label} пока нет.</p>",
                "</article>",
            ]
        )

    subtitle_parts: list[str] = []
    if payload.artist_names:
        subtitle_parts.append(", ".join(payload.artist_names))
    if payload.release_year is not None:
        subtitle_parts.append(str(payload.release_year))
    if payload.release_type:
        subtitle_parts.append(payload.release_type)
    if payload.duration_ms is not None:
        subtitle_parts.append(_format_duration_ms(payload.duration_ms))
    explainability = getattr(payload, "explainability", None)

    body = [
        "<article class='platform-card'>",
        "<div class='card-head'>",
        "<div class='card-copy'>",
        f"<h3>{label}</h3>",
        f"<p><strong>{escape(payload.label)}</strong></p>",
    ]
    if subtitle_parts:
        body.append(f"<p class='muted'>{escape(' · '.join(subtitle_parts))}</p>")
    body.append("</div><div class='badge-row'>")
    body.append(_badge(f"Есть на {label}", "platform"))
    if explainability is not None:
        body.append(_badge(_humanize_explainability(explainability.decision), _tone_for_decision(explainability.decision)))
    body.append("</div></div>")
    if payload.url:
        cta_label = "Открыть в Yandex" if provider_name == "yandex" else "Открыть в YouTube"
        body.append(f"<div class='action-row'><a class='button secondary' href='{escape(payload.url)}' target='_blank' rel='noreferrer'>{cta_label}</a></div>")
    body.append("</article>")
    return "".join(body)


def _render_yandex_catalog_sections(sections: list[ProviderCatalogSectionPayload]) -> str:
    if not sections:
        return ""

    body = ["<section class='panel'><div class='section-head'><h2>Что есть в каталоге Yandex</h2><p class='muted'>Родной каталог Yandex по этой сущности.</p></div><div class='stack'>"]
    for section in sections:
        count_label = f"{section.total_items} items" if section.total_items is not None else f"{len(section.items)} items"
        body.append("<section>")
        body.append(f"<div class='row between wrap'><h3>{escape(section.title)}</h3><span class='muted'>{escape(count_label)}</span></div>")
        if not section.items:
            body.append("<p class='empty'>В этом разделе пока нет сохраненных объектов.</p>")
        else:
            body.append("<div class='release-grid'>")
            for item in section.items:
                body.append("<article class='release-card'>")
                body.append(f"<h3>{escape(item.label)}</h3>")
                if item.subtitle:
                    body.append(f"<p class='muted'>{escape(item.subtitle)}</p>")
                else:
                    body.append(f"<p class='muted'>{escape(item.item_kind)}</p>")
                if item.url:
                    body.append(f"<div class='action-row'><a class='button secondary' href='{escape(item.url)}' target='_blank' rel='noreferrer'>Открыть в Yandex</a></div>")
                body.append("</article>")
            body.append("</div>")
        body.append("</section>")
    body.append("</div></section>")
    return "".join(body)


def _render_missing_on_yandex_view(view: MissingOnYandexViewPayload) -> str:
    if not view.items:
        return "<p class='empty'>Все связанные релизы уже подтверждены на Yandex.</p>"

    body = [
        f"<p class='muted'>{view.candidate_count} релизов требуют ручной проверки. {view.missing_count} пока не найдены в каталоге Yandex.</p>",
        "<div class='release-grid'>",
    ]
    for item in view.items:
        body.append(_render_missing_on_yandex_card(item))
    body.append("</div>")
    return "".join(body)


def _render_missing_on_yandex_card(item) -> str:
    subtitle = []
    if item.release_year is not None:
        subtitle.append(str(item.release_year))
    if item.release_type:
        subtitle.append(item.release_type)
    if item.track_count is not None:
        track_label = "трек" if item.track_count == 1 else "треков"
        subtitle.append(f"{item.track_count} {track_label}")
    if item.role:
        subtitle.append(item.role)

    badges = []
    if item.status == "catalog_candidate":
        badges.append(_badge("Есть кандидат на Yandex", "ambiguous"))
    else:
        badges.append(_badge("Не найдено на Yandex", "missing"))

    body = [
        "<article class='release-card'>",
        "<div class='row between wrap'>",
        f"<h3><a href='/ui/releases/{item.release_id}'>{escape(item.title)}</a></h3>",
        f"<div class='badge-row'>{''.join(badges)}</div>",
        "</div>",
        f"<p class='muted'>{escape(' · '.join(subtitle) if subtitle else 'Релиз')}</p>",
    ]
    if item.status == "catalog_candidate":
        for candidate in item.yandex_candidates:
            candidate_subtitle = []
            if candidate.release_year is not None:
                candidate_subtitle.append(str(candidate.release_year))
            if candidate.release_type:
                candidate_subtitle.append(candidate.release_type)
            if candidate.source_list_kinds:
                candidate_subtitle.append(", ".join(candidate.source_list_kinds))
            label = escape(candidate.label)
            if candidate.url:
                label = f"<a href='{escape(candidate.url)}' target='_blank' rel='noreferrer'>{label}</a>"
            body.append(
                f"<p class='muted'>Возможный кандидат: {label} <span class='muted'>{escape(' · '.join(candidate_subtitle))}</span></p>"
            )
    else:
        body.append("<p class='muted'>Точного совпадения в сохраненном каталоге Yandex пока нет.</p>")
    body.append(f"<div class='action-row'><a class='button secondary' href='/ui/releases/{item.release_id}'>Открыть релиз</a></div>")
    body.append("</article>")
    return "".join(body)


def _render_artist_stats(*, release_count: int, album_count: int, missing_on_yandex_count: int) -> str:
    return "".join(
        [
            "<section class='panel'><div class='stats-grid'>",
            _render_stat_card(str(release_count), "связанных релизов"),
            _render_stat_card(str(album_count), "альбомов"),
            _render_stat_card(str(missing_on_yandex_count), "без Yandex"),
            "</div></section>",
        ]
    )


def _render_stat_card(value: str, label: str) -> str:
    return (
        "<article class='stat-card'>"
        f"<strong>{escape(value)}</strong>"
        f"<span class='muted'>{escape(label)}</span>"
        "</article>"
    )


def _render_release_links(releases) -> str:
    if not releases:
        return "<p class='empty'>Связанные релизы пока не сохранены.</p>"
    body = ["<ul class='simple-list'>"]
    for release in releases:
        body.append(
            f"<li><a href='/ui/releases/{release.release_id}'>{escape(release.title)}</a> <span class='muted'>{escape(_release_meta(release.release_year, release.release_type, release.role, release.track_number))}</span></li>"
        )
    body.append("</ul>")
    return "".join(body)


def _render_release_cards(releases, *, empty_message: str) -> str:
    if not releases:
        return f"<p class='empty'>{escape(empty_message)}</p>"

    body = ["<div class='release-grid'>"]
    for release in releases:
        body.append(_render_release_card(release))
    body.append("</div>")
    return "".join(body)


def _render_release_card(release) -> str:
    badges = [_badge(platform_name.capitalize(), "platform") for platform_name in release.available_platforms]
    if release.is_missing_yandex:
        badges.append(_badge("Нет на Yandex", "missing"))

    return "".join(
        [
            "<article class='release-card'>",
            "<div class='row between wrap'>",
            f"<h3><a href='/ui/releases/{release.release_id}'>{escape(release.title)}</a></h3>",
            f"<div class='badge-row'>{''.join(badges)}</div>",
            "</div>",
            f"<p class='muted'>{escape(_release_meta(release.release_year, release.release_type, release.role, release.track_count))}</p>",
            f"<div class='action-row'><a class='button secondary' href='/ui/releases/{release.release_id}'>Открыть релиз</a></div>",
            "</article>",
        ]
    )


def _render_track_links(tracks) -> str:
    if not tracks:
        return "<p class='empty'>Связанные треки пока не сохранены.</p>"
    body = ["<ul class='simple-list'>"]
    for track in tracks:
        subtitle = []
        if track.duration_ms is not None:
            subtitle.append(_format_duration_ms(track.duration_ms))
        if track.role:
            subtitle.append(track.role)
        if track.track_number is not None:
            subtitle.append(f"#{track.track_number}")
        body.append(
            f"<li><a href='/ui/tracks/{track.track_id}'>{escape(track.title)}</a> <span class='muted'>{escape(' · '.join(subtitle))}</span></li>"
        )
    body.append("</ul>")
    return "".join(body)


def _render_notice(text: str, tone: str) -> str:
    return f"<section class='panel notice notice-{escape(tone)}'><p>{escape(text)}</p></section>"


def _render_action(action: ActionView) -> str:
    class_name = "button" if action.variant == "primary" else f"button {escape(action.variant)}"
    target = " target='_blank' rel='noreferrer'" if action.external else ""
    return f"<a class='{class_name}' href='{escape(action.href)}'{target}>{escape(action.label)}</a>"


def _render_badge_view(badge: BadgeView) -> str:
    return _badge(badge.label, badge.tone)


def _badge(label: str, tone: str) -> str:
    safe_tone = escape(tone.replace("_", "-"))
    return f"<span class='badge badge-{safe_tone}'>{escape(label)}</span>"


def _hidden_limit(limit: Optional[int]) -> str:
    if limit is None:
        return ""
    return f"<input type='hidden' name='limit' value='{limit}'>"


def _entity_platform_summary(platforms: dict[str, Optional[LinkedPlatformEntityPayload]]) -> str:
    youtube = platforms.get("youtube") is not None
    yandex = platforms.get("yandex") is not None
    if youtube and yandex:
        return "Есть на Yandex и YouTube."
    if youtube:
        return "Есть на YouTube, но подтвержденной карточки на Yandex нет."
    if yandex:
        return "Есть на Yandex, но подтвержденной карточки на YouTube нет."
    return "Подтвержденных карточек на платформах пока нет."


def _entity_availability_badges(platforms: dict[str, Optional[LinkedPlatformEntityPayload]]) -> list[BadgeView]:
    badges: list[BadgeView] = []
    if platforms.get("yandex") is not None:
        badges.append(BadgeView("Yandex", "platform"))
    else:
        badges.append(BadgeView("Нет на Yandex", "missing"))
    if platforms.get("youtube") is not None:
        badges.append(BadgeView("YouTube", "platform"))
    else:
        badges.append(BadgeView("Нет на YouTube", "warning"))
    return badges


def _humanize_explainability(decision: str) -> str:
    if decision == "auto":
        return "Подтверждено"
    if decision == "ambiguous":
        return "Вариант"
    return "Не подтверждено"


def _tone_for_decision(decision: str) -> str:
    if decision == "auto":
        return "auto"
    if decision == "ambiguous":
        return "ambiguous"
    return "warning"


def _release_meta(
    release_year: Optional[int],
    release_type: Optional[str],
    role: Optional[str],
    extra: Optional[int] = None,
) -> str:
    parts: list[str] = []
    if release_year is not None:
        parts.append(str(release_year))
    if release_type:
        parts.append(release_type)
    if role:
        parts.append(role)
    if extra is not None:
        parts.append(str(extra))
    return " · ".join(parts) if parts else "Релиз"


def _is_album_release_type(release_type: Optional[str]) -> bool:
    if release_type is None:
        return False
    return release_type in {"album", "lp", "ep"}


def _format_duration_ms(duration_ms: Optional[int]) -> str:
    if duration_ms is None:
        return ""
    total_seconds = max(0, duration_ms // 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def _render_layout(
    *,
    title: str,
    content: str,
    refresh_seconds: Optional[int] = None,
    body_attrs: Optional[dict[str, str]] = None,
) -> str:
    refresh_tag = f"<meta http-equiv='refresh' content='{refresh_seconds}'>" if refresh_seconds is not None else ""
    attrs = " ".join(
        f"{escape(key)}='{escape(value)}'"
        for key, value in (body_attrs or {}).items()
        if value
    )
    return "".join(
        [
            "<!doctype html><html lang='ru'><head><meta charset='utf-8'>",
            "<meta name='viewport' content='width=device-width, initial-scale=1'>",
            f"<title>{escape(title)} · NETvRF</title>",
            refresh_tag,
            "<link rel='stylesheet' href='/static/app.css'>",
            "<script defer src='/static/app.js'></script>",
            "</head>",
            f"<body {attrs}>",
            "<header class='site-header'><a class='brand' href='/ui'>NETvRF</a><nav><a href='/ui'>Поиск</a></nav></header>",
            "<main class='shell'>",
            content,
            "</main></body></html>",
        ]
    )
