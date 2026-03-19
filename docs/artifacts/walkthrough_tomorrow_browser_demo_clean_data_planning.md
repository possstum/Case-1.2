# Walkthrough: Planning Tomorrow Browser Demo With Clean Data

Status: completed on `2026-03-19`.

## Goal

Prepare a concrete tomorrow implementation plan so the project can be presented through a browser search flow from a clean environment.

## Scope

- `docs/artifacts/implementation_plan_tomorrow_browser_demo_clean_data.md`
- `docs/artifacts/walkthrough_tomorrow_browser_demo_clean_data_planning.md`

Out of scope:

- `app/*`
- `tests/*`
- runtime mutations
- infra changes

## Milestone Log

### Milestone 1: Planning Artifact

Changed files:

- `docs/artifacts/implementation_plan_tomorrow_browser_demo_clean_data.md`
- `docs/artifacts/walkthrough_tomorrow_browser_demo_clean_data_planning.md`

Commands run:

- `rg -n "seed_catalog|clean data|demo|staging-like|run_worker|run_api|search:v2|Krovostok|Motorama|ui\\?q=|artist overview|yandex_catalog_sections" docs app tests scripts README.md`
- `rg --files scripts app tests docs/artifacts`
- `sed -n '1,560p' tests/test_support.py`
- `sed -n '1,260p' app/services/search_service.py`
- `sed -n '1,260p' app/api/routes/search.py`
- `sed -n '1,260p' app/web/render.py`

Tests run:

- none

Key findings used in the plan:

- there is already a browser UI at `/ui`
- current WIP already includes a primary artist CTA path via `Open artist overview`
- current search cache version is `search:v2`
- test-only seeding exists via `tests/test_support.py:seed_catalog(...)`, but there is no runtime/demo reset tool
- the historically accepted live search probe set is currently narrow and centered on `Krovostok` and `Motorama`
- existing artifacts already prove parts of the browser/sync story, but there is no single clean-data browser-demo runbook yet

## Final Outcome

- prepared a concrete tomorrow execution plan
- kept the change limited to `docs/artifacts`
- did not alter application code or runtime behavior
