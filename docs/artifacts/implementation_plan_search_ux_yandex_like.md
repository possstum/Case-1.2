# Implementation Plan: Search UX Closer To Yandex Music

Status: created on `2026-03-20`.

## Summary

- Goal: turn `/ui` and the entity detail pages into a product-first music search experience with tabs, category blocks, availability badges, and a clear `Нет в РФ` flow, without changing the core matching logic.
- Keep `/search` and the entity JSON contracts unchanged. Implement the UX shift in the web layer plus small internal presenter helpers.
- Main design choice: `Все` and `Нет в РФ` will use three explicit kind-specific searches (`artist`, `release`, `track`) instead of one `kind=None` call.

## Grounded facts

- The current UI is fully server-rendered in `app/web/render.py` and still leads with hero copy, `query/kind/limit`, generic result cards, cache/partial emphasis, and raw `features_json`.
- The current UI assertions in `tests/api/test_web_ui.py` explicitly lock in engineering-heavy copy and visible explainability JSON.
- The existing search payload already exposes what the new UX needs: `kind`, `results`, `platforms`, `missing_platforms`, `decision`, `score`.
- The existing detail payloads already expose enough availability state for product rendering: `platforms`, `missing_platforms`, `partial`, and artist-specific `missing_on_yandex_view`.
- In both provider clients, `search(kind=None)` loops all three kinds and trims the combined list to `items[:limit]`, so one mixed search cannot reliably power the new `Все` tab.

## Public interfaces and internal additions

- `/ui` gains optional `tab` query param with values `all|artist|release|track|missing`.
- `/ui` keeps accepting legacy `kind` and `limit`; `kind` is treated as an input alias when `tab` is absent, and all new UI links/forms emit `tab`.
- `/search`, `/artists/{id}`, `/releases/{id}`, and `/tracks/{id}` JSON schemas stay unchanged.
- Add internal web-layer presenter helpers in `app/web/presenters.py` for tab resolution, grouped sections, availability badges, human status labels, and `Нет в РФ` classification.
- Keep the app SSR-only for this milestone. No SPA migration and no JS search transport.

## Milestones

### Milestone 0: Planning Artifacts

Subsystem:

- docs/artifacts

Files:

- `docs/artifacts/implementation_plan_search_ux_yandex_like.md`
- `docs/artifacts/walkthrough_search_ux_yandex_like.md`

Edits:

- create the implementation-plan artifact first
- create the walkthrough shell
- record grounded facts and milestone boundaries
- do not change application code in this milestone

Validation:

- `sed -n '1,240p' docs/artifacts/implementation_plan_search_ux_yandex_like.md`
- `sed -n '1,240p' docs/artifacts/walkthrough_search_ux_yandex_like.md`
- `git status --short`

Tests:

- none

### Milestone 1: Search Page Orchestration And Presenter Layer

Subsystem:

- web search UI logic

Files:

- `app/web/routes.py`
- `app/web/presenters.py`
- `tests/web/test_presenters.py`
- `tests/api/test_web_ui.py`
- `docs/artifacts/walkthrough_search_ux_yandex_like.md`

Edits:

- add tab resolution
- keep `q` in URL
- preserve the selected tab on submit
- remove the visible `kind` control
- keep `limit` as hidden and legacy URL state
- build `all` and `missing` from three kind-specific searches
- build specific tabs from one search
- compute featured artist, grouped sections, availability badges, human status labels, and page-level provider-outage notices without changing API contracts

Validation:

- `.venv/bin/ruff check app/web tests/api/test_web_ui.py tests/web/test_presenters.py`

Tests:

- `.venv/bin/pytest -q tests/web/test_presenters.py tests/api/test_web_ui.py`

### Milestone 2: `/ui` Information Architecture And Rendering Refresh

Subsystem:

- web search rendering

Files:

- `app/web/render.py`
- `app/web/static/app.css`
- `tests/api/test_web_ui.py`
- `docs/artifacts/walkthrough_search_ux_yandex_like.md`

Edits:

- replace the heavy hero with a compact search-first landing
- add a sticky search bar plus tab row
- render `Все` as featured artist plus preview blocks for `Исполнители`, `Альбомы`, and `Треки`
- render specific tabs as fast-scanning card lists
- render `Нет в РФ` as grouped missing and unconfirmed sections with human reasons
- move raw JSON into collapsed technical details
- demote cache, partial, and provider-debug text to secondary notices only

Validation:

- `.venv/bin/ruff check app/web/render.py app/web/static/app.css tests/api/test_web_ui.py`

Tests:

- `.venv/bin/pytest -q tests/api/test_web_ui.py`

### Milestone 3: Entity Detail Availability Refresh

Subsystem:

- web entity-detail rendering

Files:

- `app/web/render.py`
- `app/web/static/app.css`
- `tests/api/test_web_ui.py`
- `tests/api/test_entities.py`
- `docs/artifacts/walkthrough_search_ux_yandex_like.md`

Edits:

- replace generic platform cards with top availability summaries for artist, release, and track pages
- show Yandex and YouTube presence immediately
- render missing-on-Yandex as a product status instead of a technical absence
- keep platform links as user-facing action blocks
- push JSON and sync controls into a secondary technical area
- keep artist Yandex catalog and missing-on-Yandex data, but rename and reorder sections to read like product information

Validation:

- `.venv/bin/ruff check app/web/render.py app/web/static/app.css tests/api/test_web_ui.py tests/api/test_entities.py`

Tests:

- `.venv/bin/pytest -q tests/api/test_web_ui.py tests/api/test_entities.py`

### Milestone 4: Regression Pass And Final Walkthrough

Subsystem:

- tests and docs evidence

Files:

- `tests/web/test_presenters.py`
- `tests/api/test_web_ui.py`
- `tests/api/test_entities.py`
- `tests/api/test_search.py`
- `docs/artifacts/walkthrough_search_ux_yandex_like.md`

Edits:

- close regressions from the tabbed UX
- document the exact `Нет в РФ` rules
- call out unresolved provider-dependent live limitations
- record the final changed-files list, commands, and tests in the walkthrough

Validation:

- `.venv/bin/pytest -q tests/web/test_presenters.py tests/api/test_web_ui.py tests/api/test_entities.py tests/api/test_search.py`
- `.venv/bin/pytest -q`

Tests:

- explicit HTML and response-shape assertions; no snapshot suite is introduced in this milestone

## UX rules

- Product copy on `/ui` and the detail pages moves to Russian for search and status language. JSON/API contracts stay unchanged and no i18n framework is introduced.
- Tab labels are `Все`, `Треки`, `Альбомы`, `Исполнители`, `Нет в РФ`.
- Human status mapping is fixed:
  - `auto` -> confirmed match
  - `ambiguous` -> possible match
  - `reject` with a Yandex candidate -> Yandex match not confirmed
  - `reject` with YouTube-only evidence -> found on YouTube, not found on Yandex
- `Нет в РФ` includes only results with non-Yandex evidence plus no confirmed Yandex presence.
- If Yandex is unavailable for a response, the UI shows a neutral availability-unknown warning and does not classify those results as `Нет в РФ`.
- Cards open canonical detail pages when `canonical_id` exists. If no canonical entity exists, the primary CTA falls back to the provider URL.
- `cache`, `miss`, `stale`, `partial`, raw `reject`, and `features_json` do not lead the main user flow.

## Acceptance scenarios

- A mixed stub query renders separate `Исполнители`, `Альбомы`, and `Треки` blocks on `tab=all`, with the best artist featured first and alternative candidates still visible.
- `tab=artist`, `tab=release`, and `tab=track` each render only that entity kind and preserve `q` plus `limit` in navigation.
- `tab=missing` includes YouTube-only and unconfirmed Yandex matches, excludes Yandex-only rejects, and shows a neutral warning instead of `Нет в РФ` when Yandex is unavailable.
- Release cards show artist names plus year and type; track cards show artist names plus duration; both surface Yandex and YouTube availability clearly.
- Artist, release, and track detail pages immediately show Yandex and YouTube presence and a clear missing-on-Yandex status where relevant.
- Raw `features_json` is absent from the primary result flow and appears only inside collapsed technical details.
- Legacy `/ui?q=...&kind=artist` continues to work and renders the artists tab without breaking existing links.

## Assumptions and defaults

- No backend API or DB schema change is planned.
- `SEARCH_DEFAULT_LIMIT` remains the backend default. The visible numeric limit input is removed from the product UI, while the URL param stays supported for manual overrides and tests.
- `Все` preview sections show the top 3 items per category. Dedicated tabs show all returned items up to the effective limit.
- Out of scope:
  - player
  - auth
  - recommendations
  - left-nav shell
  - provider ranking rewrite
  - canonical row creation for reject-only results without an existing overview page
