# Walkthrough: Search UX Closer To Yandex Music

Status: started on `2026-03-20`.

## Goal

Rework the server-rendered NETvRF search and entity detail UX so that it reads like a music search tool with clear tabs, availability states, and a dedicated `Нет в РФ` scenario, while preserving the backend matching model and API contracts.

## Milestones

### Milestone 0: Planning Artifacts

Changed files:

- `docs/artifacts/implementation_plan_search_ux_yandex_like.md`
- `docs/artifacts/walkthrough_search_ux_yandex_like.md`

Commands run:

```bash
git status --short
```

```bash
sed -n '1,240p' docs/artifacts/implementation_plan_search_ux_yandex_like.md
```

```bash
sed -n '1,240p' docs/artifacts/walkthrough_search_ux_yandex_like.md
```

Tests run:

- none

Notes:

- Planning artifacts were created first, before application code changes.

### Milestone 1: Search Page Orchestration And Presenter Layer

Changed files:

- `app/web/routes.py`
- `app/web/presenters.py`
- `tests/web/test_presenters.py`
- `tests/api/test_web_ui.py`
- `docs/artifacts/walkthrough_search_ux_yandex_like.md`

Commands run:

```bash
.venv/bin/ruff check app/web tests/web/test_presenters.py tests/api/test_web_ui.py
```

```bash
.venv/bin/pytest -q tests/web/test_presenters.py tests/api/test_web_ui.py
```

Tests run:

- `.venv/bin/pytest -q tests/web/test_presenters.py tests/api/test_web_ui.py`
  - `18 passed in 0.64s`

Notes:

- `/ui` now accepts `tab=all|artist|release|track|missing`.
- legacy `kind` is still accepted and treated as an alias when `tab` is absent.
- `tab=all` and `tab=missing` execute three explicit searches: `artist`, `release`, `track`.
- presenter helpers now own tab resolution, human status mapping, availability badges, and `Нет в РФ` classification.

### Milestone 2: `/ui` Information Architecture And Rendering Refresh

Changed files:

- `app/web/render.py`
- `app/web/static/app.css`
- `tests/api/test_web_ui.py`
- `docs/artifacts/walkthrough_search_ux_yandex_like.md`

Commands run:

```bash
.venv/bin/ruff check app/web tests/web/test_presenters.py tests/api/test_web_ui.py
```

```bash
.venv/bin/pytest -q tests/web/test_presenters.py tests/api/test_web_ui.py
```

Tests run:

- `.venv/bin/pytest -q tests/web/test_presenters.py tests/api/test_web_ui.py`
  - `18 passed in 0.64s`

Notes:

- `/ui` now renders a compact search-first shell instead of the old MVP hero/debug screen.
- tabs are visible at the top and preserve the query in URL links.
- `Все` renders:
  - featured artist spotlight
  - separate `Исполнители`, `Альбомы`, and `Треки` sections
- `Нет в РФ` renders:
  - `Есть на YouTube, не найдено на Yandex`
  - `Совпадение на Yandex не подтверждено`
- raw `features_json` moved behind collapsible `Технические детали`.

### Milestone 3: Entity Detail Availability Refresh

Changed files:

- `app/web/render.py`
- `app/web/static/app.css`
- `tests/api/test_web_ui.py`
- `docs/artifacts/walkthrough_search_ux_yandex_like.md`

Commands run:

```bash
.venv/bin/pytest -q tests/api/test_entities.py tests/api/test_search.py
```

Tests run:

- `.venv/bin/pytest -q tests/api/test_entities.py tests/api/test_search.py`
  - `21 passed in 1.67s`

Notes:

- artist, release, and track pages now open with a product availability summary instead of leading with technical platform cards.
- platform links were reshaped into user-facing availability blocks with secondary technical details.
- artist page keeps Yandex catalog and missing-on-Yandex data, but presents them with product copy:
  - `Что есть в каталоге Yandex`
  - `Нет на Yandex`
- JSON and sync controls moved into a secondary `Технические детали` area.

### Milestone 4: Regression Pass And Final Wrap-Up

Changed files:

- `docs/artifacts/walkthrough_search_ux_yandex_like.md`

Commands run:

```bash
.venv/bin/pytest -q
```

```bash
git status --short -- app/web/routes.py app/web/render.py app/web/static/app.css app/web/presenters.py tests/web/test_presenters.py tests/api/test_web_ui.py docs/artifacts/implementation_plan_search_ux_yandex_like.md docs/artifacts/walkthrough_search_ux_yandex_like.md
```

Tests run:

- `.venv/bin/pytest -q`
  - `109 passed in 3.94s`

## Final notes

- Changed files in this implementation slice:
  - `app/web/routes.py`
  - `app/web/render.py`
  - `app/web/static/app.css`
  - `app/web/presenters.py`
  - `tests/api/test_web_ui.py`
  - `tests/web/test_presenters.py`
  - `docs/artifacts/implementation_plan_search_ux_yandex_like.md`
  - `docs/artifacts/walkthrough_search_ux_yandex_like.md`
- How search works now:
  - `tab=artist|release|track` performs one search request for that entity kind.
  - `tab=all|missing` performs three search requests and builds the page from grouped kind-specific responses.
  - `q` stays in the URL and tab links preserve `q` and `limit`.
- How `Нет в РФ` is determined:
  - include only items with non-Yandex evidence and known Yandex status
  - include `YouTube-only` results where `youtube` exists and `yandex` is absent
  - include `unconfirmed` results where `youtube` exists, a Yandex candidate exists, but `decision=reject`
  - exclude `Yandex-only` unmatched results
  - if `yandex` is listed in `missing_platforms`, show a warning and do not classify those results as `Нет в РФ`
- Edge cases covered:
  - legacy `kind` links still work
  - ambiguous results stay visible as `Возможный вариант`
  - reject results fall back to provider URLs when there is no canonical detail page
  - provider outage is presented separately from platform absence
  - `Альбомы` tab still uses backend `release` results, so EP/single cases remain visible and keep their type metadata
- Deliberate tradeoffs:
  - used three backend searches for `Все` and `Нет в РФ` to avoid mixed-search truncation bias
  - kept SSR rendering only; no SPA migration
  - kept backend search/detail JSON contracts unchanged
- Follow-up UX cleanup on `2026-03-20`:
  - removed visible technical UI from search and detail pages
  - removed `Технические детали`, `JSON API`, and search debug panels from the user flow
  - removed `Canonical id` from entity hero blocks
  - simplified the header to a search-only navigation
  - added an explicit `Карточка ... ещё наполняется` state for entities that only have platform links but no hydrated releases/tracks/catalog data yet
  - kept the refresh action, but relabeled it as a user-facing `Обновить карточку`
- Additional validation after the cleanup:
  - `.venv/bin/pytest -q tests/api/test_web_ui.py`
    - `14 passed in 0.66s`
  - `.venv/bin/pytest -q`
    - `110 passed in 3.12s`
- Out of scope:
  - player
  - auth
  - recommendations
  - left-side music-app shell
  - provider ranking rewrite
  - canonical entity creation for reject-only results without an existing canonical row
