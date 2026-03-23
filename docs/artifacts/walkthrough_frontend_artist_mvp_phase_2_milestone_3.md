# Walkthrough: Frontend Artist MVP Phase 2 Milestone 3

Status: completed on `2026-03-19`.

## Goal

Move `Missing on Yandex` from a simple filter over canonical release links to a dedicated artist-level comparison read model.

## Changed Files

- `app/api/schemas/entities.py`
- `app/services/artist_service.py`
- `app/web/render.py`
- `tests/test_support.py`
- `tests/api/test_entities.py`
- `tests/api/test_web_ui.py`
- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_3.md`

## Commands Run

```bash
./.venv/bin/ruff check app/api/schemas/entities.py app/services/artist_service.py app/web/render.py tests/test_support.py tests/api/test_entities.py tests/api/test_web_ui.py
```

```bash
./.venv/bin/python -m pytest -q tests/api/test_entities.py tests/api/test_web_ui.py
```

## Tests Run

- `./.venv/bin/ruff check app/api/schemas/entities.py app/services/artist_service.py app/web/render.py tests/test_support.py tests/api/test_entities.py tests/api/test_web_ui.py` -> `All checks passed!`
- `./.venv/bin/python -m pytest -q tests/api/test_entities.py tests/api/test_web_ui.py` -> `21 passed in 2.13s`

## Result

`ArtistDetailResponse` now includes a dedicated `missing_on_yandex_view` with summary counts and item-level statuses. The read model compares unresolved canonical releases against stored Yandex artist catalog lists and distinguishes between:

- releases that still have no Yandex evidence in the stored artist catalog
- releases that already have provider-native Yandex candidates but still lack a canonical Yandex link

The artist page now renders `Missing on Yandex` from that read model instead of filtering the generic release list.
