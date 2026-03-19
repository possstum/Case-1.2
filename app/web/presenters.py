from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Optional
from urllib.parse import urlencode

from app.api.schemas.search import SearchPlatformEntityPayload, SearchResponse, SearchResultItemPayload

SearchTabKey = Literal["all", "artist", "release", "track", "missing"]

TAB_ORDER: tuple[SearchTabKey, ...] = ("all", "track", "release", "artist", "missing")
TAB_LABELS: dict[SearchTabKey, str] = {
    "all": "Все",
    "track": "Треки",
    "release": "Альбомы",
    "artist": "Исполнители",
    "missing": "Нет в РФ",
}
KIND_LABELS = {
    "artist": "Исполнитель",
    "release": "Релиз",
    "track": "Трек",
}


@dataclass(frozen=True)
class BadgeView:
    label: str
    tone: str


@dataclass(frozen=True)
class ActionView:
    label: str
    href: str
    external: bool = False
    variant: str = "secondary"


@dataclass(frozen=True)
class SearchTabView:
    key: SearchTabKey
    label: str
    href: str
    active: bool


@dataclass(frozen=True)
class SearchNoticeView:
    text: str
    tone: str = "info"


@dataclass(frozen=True)
class SearchResponseDebugView:
    kind: str
    cache_status: str
    partial: bool
    missing_platforms: list[str]
    result_count: int


@dataclass(frozen=True)
class SearchCardView:
    card_id: str
    kind: str
    kind_label: str
    title: str
    subtitle: str
    meta: Optional[str]
    note: Optional[str]
    badges: list[BadgeView]
    primary_action: Optional[ActionView]
    provider_actions: list[ActionView]
    technical_json: dict[str, Any]


@dataclass(frozen=True)
class SearchSectionView:
    key: str
    title: str
    description: Optional[str]
    items: list[SearchCardView]
    empty_message: str


@dataclass(frozen=True)
class SearchPageView:
    query: str
    active_tab: SearchTabKey
    tabs: list[SearchTabView]
    notices: list[SearchNoticeView]
    featured_artist: Optional[SearchCardView]
    sections: list[SearchSectionView]
    empty_title: str
    empty_text: str
    response_debug: list[SearchResponseDebugView] = field(default_factory=list)


def resolve_search_tab(tab: Optional[str], kind: Optional[str]) -> SearchTabKey:
    if tab in TAB_LABELS:
        return tab  # type: ignore[return-value]
    if kind in {"artist", "release", "track"}:
        return kind  # type: ignore[return-value]
    return "all"


def requested_kinds_for_tab(active_tab: SearchTabKey) -> tuple[str, ...]:
    if active_tab in {"all", "missing"}:
        return ("artist", "release", "track")
    return (active_tab,)


def build_search_page_view(
    *,
    query: str,
    active_tab: SearchTabKey,
    limit: Optional[int],
    responses_by_kind: Mapping[str, SearchResponse],
    provider_notice: Optional[str] = None,
) -> SearchPageView:
    tabs = build_tab_views(query=query, active_tab=active_tab, limit=limit)
    if not query:
        return SearchPageView(
            query=query,
            active_tab=active_tab,
            tabs=tabs,
            notices=[],
            featured_artist=None,
            sections=[],
            empty_title="Найдите музыку",
            empty_text="Ищите исполнителей, альбомы и треки. Вкладка «Нет в РФ» покажет только случаи без подтвержденного результата на Yandex.",
        )

    notices: list[SearchNoticeView] = []
    if provider_notice:
        notices.append(SearchNoticeView(text=provider_notice, tone="warning"))

    debug_rows = [_debug_view(kind, response) for kind, response in responses_by_kind.items()]
    if any("yandex" in response.missing_platforms for response in responses_by_kind.values()):
        notices.append(
            SearchNoticeView(
                text="Yandex сейчас ответил не на все запросы. Это не то же самое, что отсутствие релиза на платформе.",
                tone="warning",
            )
        )
    if any("youtube" in response.missing_platforms for response in responses_by_kind.values()):
        notices.append(
            SearchNoticeView(
                text="YouTube сейчас ответил не на все запросы. Показываем только то, что удалось подтвердить.",
                tone="info",
            )
        )

    responses = dict(responses_by_kind)
    if active_tab == "all":
        artist_cards = _cards_from_response(responses.get("artist"))
        featured_artist = artist_cards[0] if artist_cards else None
        artist_preview = artist_cards[1:4] if featured_artist is not None else artist_cards[:3]
        release_preview = _cards_from_response(responses.get("release"))[:3]
        track_preview = _cards_from_response(responses.get("track"))
        sections = [
            SearchSectionView(
                key="artists",
                title="Исполнители",
                description="Вероятные варианты по запросу.",
                items=artist_preview,
                empty_message="Исполнители по этому запросу пока не нашлись.",
            ),
            SearchSectionView(
                key="releases",
                title="Альбомы",
                description="Релизы, которые могут относиться к запросу.",
                items=release_preview,
                empty_message="Альбомы и релизы по запросу пока не нашлись.",
            ),
            SearchSectionView(
                key="tracks",
                title="Треки",
                description="Все найденные треки и версии по запросу.",
                items=track_preview,
                empty_message="Треки по запросу пока не нашлись.",
            ),
        ]
        return SearchPageView(
            query=query,
            active_tab=active_tab,
            tabs=tabs,
            notices=notices,
            featured_artist=featured_artist,
            sections=sections,
            empty_title="Пока ничего не найдено",
            empty_text="Попробуйте уточнить запрос или переключиться между вкладками.",
            response_debug=debug_rows,
        )

    if active_tab == "missing":
        youtube_only_cards: list[SearchCardView] = []
        unconfirmed_cards: list[SearchCardView] = []
        unknown_kinds: list[str] = []
        for kind_name in ("artist", "release", "track"):
            response = responses.get(kind_name)
            if response is None:
                continue
            if "yandex" in response.missing_platforms:
                unknown_kinds.append(KIND_LABELS.get(kind_name, kind_name).lower())
                continue
            youtube_only_cards.extend(_cards_from_response(response, missing_filter="youtube_only"))
            unconfirmed_cards.extend(_cards_from_response(response, missing_filter="unconfirmed"))

        if unknown_kinds:
            notices.append(
                SearchNoticeView(
                    text=f"Для части результатов не удалось проверить Yandex: {', '.join(unknown_kinds)}.",
                    tone="warning",
                )
            )

        return SearchPageView(
            query=query,
            active_tab=active_tab,
            tabs=tabs,
            notices=notices,
            featured_artist=None,
            sections=[
                SearchSectionView(
                    key="youtube-only",
                    title="Есть на YouTube, не найдено на Yandex",
                    description="Показываем только результаты с подтвержденным присутствием вне Yandex.",
                    items=youtube_only_cards,
                    empty_message="Подтвержденных YouTube-only результатов по этому запросу нет.",
                ),
                SearchSectionView(
                    key="unconfirmed-yandex",
                    title="Совпадение на Yandex не подтверждено",
                    description="Есть кандидат на Yandex, но уверенного совпадения нет.",
                    items=unconfirmed_cards,
                    empty_message="Неоднозначных совпадений с Yandex по этому запросу нет.",
                ),
            ],
            empty_title="Сценарий «Нет в РФ» пуст",
            empty_text="Либо всё уже подтверждено на Yandex, либо для этого запроса пока не хватило данных.",
            response_debug=debug_rows,
        )

    response = responses.get(active_tab)
    cards = _cards_from_response(response)
    section_titles = {
        "artist": "Исполнители",
        "release": "Альбомы",
        "track": "Треки",
    }
    section_descriptions = {
        "artist": "Кого вы, вероятно, имели в виду.",
        "release": "Релизы, отсортированные по качеству совпадения.",
        "track": "Треки, отсортированные по качеству совпадения.",
    }
    return SearchPageView(
        query=query,
        active_tab=active_tab,
        tabs=tabs,
        notices=notices,
        featured_artist=None,
        sections=[
            SearchSectionView(
                key=active_tab,
                title=section_titles[active_tab],
                description=section_descriptions[active_tab],
                items=cards,
                empty_message=f"Во вкладке «{TAB_LABELS[active_tab]}» по этому запросу пока ничего нет.",
            )
        ],
        empty_title="Пока ничего не найдено",
        empty_text="Попробуйте уточнить запрос или переключиться на другую вкладку.",
        response_debug=debug_rows,
    )


def build_tab_views(*, query: str, active_tab: SearchTabKey, limit: Optional[int]) -> list[SearchTabView]:
    return [
        SearchTabView(
            key=tab_key,
            label=TAB_LABELS[tab_key],
            href=_build_tab_href(query=query, tab=tab_key, limit=limit),
            active=tab_key == active_tab,
        )
        for tab_key in TAB_ORDER
    ]


def classify_missing_result(
    item: SearchResultItemPayload,
    *,
    yandex_status_known: bool,
) -> Optional[str]:
    youtube_payload = item.platforms.get("youtube")
    yandex_payload = item.platforms.get("yandex")
    if not yandex_status_known or youtube_payload is None:
        return None
    if item.decision == "reject" and yandex_payload is not None:
        return "unconfirmed"
    if yandex_payload is None:
        return "youtube_only"
    return None


def human_status_label(
    item: SearchResultItemPayload,
    *,
    yandex_status_known: bool,
) -> str:
    youtube_payload = item.platforms.get("youtube")
    yandex_payload = item.platforms.get("yandex")
    if item.decision == "auto":
        return "Подтверждено"
    if item.decision == "ambiguous":
        return "Возможный вариант"
    if youtube_payload is not None and yandex_payload is not None and yandex_status_known:
        return "Не подтверждено"
    if youtube_payload is not None and yandex_payload is None and yandex_status_known:
        return "Нет на Yandex"
    if yandex_payload is not None and youtube_payload is None:
        return "Только Yandex"
    return "Без подтверждения"


def _cards_from_response(
    response: SearchResponse | None,
    *,
    missing_filter: Optional[str] = None,
) -> list[SearchCardView]:
    if response is None:
        return []
    yandex_status_known = "yandex" not in response.missing_platforms
    cards: list[SearchCardView] = []
    for item in response.results:
        classification = classify_missing_result(item, yandex_status_known=yandex_status_known)
        if missing_filter is not None and classification != missing_filter:
            continue
        if missing_filter is None or classification is not None or item.platforms.get("youtube") is not None or item.platforms.get("yandex") is not None:
            cards.append(_card_from_item(item, yandex_status_known=yandex_status_known))
    return cards


def _card_from_item(item: SearchResultItemPayload, *, yandex_status_known: bool) -> SearchCardView:
    primary_payload = _primary_payload(item)
    title = primary_payload.label if primary_payload is not None else f"{KIND_LABELS.get(item.kind, item.kind)} без названия"
    subtitle = _subtitle_for_item(item, primary_payload)
    meta = _meta_for_item(item, primary_payload)
    badges = [BadgeView(label=KIND_LABELS.get(item.kind, item.kind), tone="kind")]
    badges.append(BadgeView(label=human_status_label(item, yandex_status_known=yandex_status_known), tone=_status_tone(item)))

    youtube_payload = item.platforms.get("youtube")
    yandex_payload = item.platforms.get("yandex")
    if yandex_payload is not None:
        badges.append(BadgeView(label="Yandex", tone="platform"))
    elif yandex_status_known and youtube_payload is not None:
        badges.append(BadgeView(label="Нет на Yandex", tone="missing"))
    if youtube_payload is not None:
        badges.append(BadgeView(label="YouTube", tone="platform"))
    if classify_missing_result(item, yandex_status_known=yandex_status_known) is not None:
        badges.append(BadgeView(label="Нет в РФ", tone="missing"))

    primary_action = _primary_action(item)
    provider_actions = _provider_actions(item)
    return SearchCardView(
        card_id=_card_id(item),
        kind=item.kind,
        kind_label=KIND_LABELS.get(item.kind, item.kind),
        title=title,
        subtitle=subtitle,
        meta=meta,
        note=_note_for_item(item, yandex_status_known=yandex_status_known),
        badges=badges,
        primary_action=primary_action,
        provider_actions=provider_actions,
        technical_json={
            "kind": item.kind,
            "canonical_id": item.canonical_id,
            "decision": item.decision,
            "score": item.score,
            "platforms": {
                provider_name: {
                    "provider_id": payload.provider_id,
                    "label": payload.label,
                    "url": payload.url,
                }
                for provider_name, payload in item.platforms.items()
                if payload is not None
            },
            "features_json": item.features_json,
        },
    )


def _card_id(item: SearchResultItemPayload) -> str:
    youtube_payload = item.platforms.get("youtube")
    yandex_payload = item.platforms.get("yandex")
    youtube_id = youtube_payload.provider_id if youtube_payload is not None else "none"
    yandex_id = yandex_payload.provider_id if yandex_payload is not None else "none"
    return f"{item.kind}:{item.canonical_id or 'none'}:{youtube_id}:{yandex_id}"


def _primary_payload(item: SearchResultItemPayload) -> SearchPlatformEntityPayload | None:
    return item.platforms.get("yandex") or item.platforms.get("youtube")


def _subtitle_for_item(
    item: SearchResultItemPayload,
    payload: SearchPlatformEntityPayload | None,
) -> str:
    if item.kind == "artist":
        return "Исполнитель"
    if payload is None:
        return KIND_LABELS.get(item.kind, item.kind)
    if payload.artist_names:
        return ", ".join(payload.artist_names)
    return KIND_LABELS.get(item.kind, item.kind)


def _meta_for_item(
    item: SearchResultItemPayload,
    payload: SearchPlatformEntityPayload | None,
) -> Optional[str]:
    if payload is None:
        return None
    parts: list[str] = []
    if item.kind == "release":
        if payload.release_year is not None:
            parts.append(str(payload.release_year))
        if payload.release_type:
            parts.append(payload.release_type)
        if payload.track_count is not None:
            track_label = "трек" if payload.track_count == 1 else "треков"
            parts.append(f"{payload.track_count} {track_label}")
    elif item.kind == "track":
        if payload.duration_ms is not None:
            parts.append(_format_duration_ms(payload.duration_ms))
    return " · ".join(parts) if parts else None


def _note_for_item(
    item: SearchResultItemPayload,
    *,
    yandex_status_known: bool,
) -> Optional[str]:
    youtube_payload = item.platforms.get("youtube")
    yandex_payload = item.platforms.get("yandex")
    if item.decision == "auto":
        return "Совпадение подтверждено между источниками."
    if item.decision == "ambiguous":
        return "Показываем как возможный вариант, потому что совпадение не полностью однозначно."
    if youtube_payload is not None and yandex_payload is not None and yandex_status_known:
        return "Есть кандидат на Yandex, но уверенного совпадения нет."
    if youtube_payload is not None and yandex_payload is None and yandex_status_known:
        return "Есть на YouTube, но подтвержденного результата на Yandex нет."
    if yandex_payload is not None and youtube_payload is None:
        return "Найдено только на Yandex."
    if not yandex_status_known:
        return "Статус Yandex сейчас не удалось проверить."
    return None


def _status_tone(item: SearchResultItemPayload) -> str:
    if item.decision == "auto":
        return "auto"
    if item.decision == "ambiguous":
        return "ambiguous"
    return "warning"


def _primary_action(item: SearchResultItemPayload) -> ActionView | None:
    if item.canonical_id is not None:
        if item.kind == "artist":
            return ActionView(label="Открыть карточку", href=f"/ui/artists/{item.canonical_id}", variant="primary")
        if item.kind == "release":
            return ActionView(label="Открыть релиз", href=f"/ui/releases/{item.canonical_id}", variant="primary")
        if item.kind == "track":
            return ActionView(label="Открыть трек", href=f"/ui/tracks/{item.canonical_id}", variant="primary")

    youtube_payload = item.platforms.get("youtube")
    yandex_payload = item.platforms.get("yandex")
    fallback_payload = youtube_payload or yandex_payload
    if fallback_payload is None or fallback_payload.url is None:
        return None
    label = "Открыть на YouTube" if fallback_payload.provider == "youtube" else "Открыть на Yandex"
    return ActionView(label=label, href=fallback_payload.url, external=True, variant="primary")


def _provider_actions(item: SearchResultItemPayload) -> list[ActionView]:
    actions: list[ActionView] = []
    for provider_name, label in (("yandex", "Yandex"), ("youtube", "YouTube")):
        payload = item.platforms.get(provider_name)
        if payload is None or payload.url is None:
            continue
        actions.append(ActionView(label=label, href=payload.url, external=True))
    return actions


def _format_duration_ms(duration_ms: int) -> str:
    total_seconds = max(0, duration_ms // 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def _build_tab_href(*, query: str, tab: SearchTabKey, limit: Optional[int]) -> str:
    params: list[tuple[str, str]] = [("tab", tab)]
    if query:
        params.append(("q", query))
    if limit is not None:
        params.append(("limit", str(limit)))
    encoded = urlencode(params)
    return f"/ui?{encoded}" if encoded else "/ui"


def _debug_view(kind: str, response: SearchResponse) -> SearchResponseDebugView:
    return SearchResponseDebugView(
        kind=kind,
        cache_status=response.cache.status,
        partial=response.partial,
        missing_platforms=list(response.missing_platforms),
        result_count=len(response.results),
    )
