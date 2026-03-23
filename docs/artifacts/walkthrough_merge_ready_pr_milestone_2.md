# Walkthrough: Merge-Ready PR Milestone 2

Status: completed on `2026-03-19`.

## Goal

Align the remaining docs and artifacts with the narrowed PR scope, and keep production-like verification as a separate milestone.

## What Changed

- removed demo-layer references from `docs/project_brief.md`
- added a separate production-like verification artifact
- added a reusable PR draft artifact
- updated `.gitignore` to keep `.env.save` and `netvrf.egg-info/` out of future PR noise

## Changed Files In This Milestone

- `.gitignore`
- `docs/project_brief.md`
- `docs/artifacts/production_like_verification.md`
- `docs/artifacts/pr_yandex_catalog_ingest.md`

## Commands Run

```bash
rg -n "app\.demo|demo data|demo loader|910001|920001|930001|demo krovostok|demo studio session|demo biography" docs/project_brief.md docs/artifacts/implementation_plan_yandex_catalog.md docs/artifacts/walkthrough_yandex_catalog.md docs/artifacts/walkthrough_yandex_catalog_milestone_1.md docs/artifacts/walkthrough_yandex_catalog_milestone_2.md docs/artifacts/walkthrough_yandex_catalog_milestone_3.md docs/artifacts/walkthrough_yandex_catalog_milestone_4.md docs/artifacts/walkthrough_yandex_catalog_milestone_5.md docs/artifacts/implementation_plan_yandex_search_auth_fix.md docs/artifacts/implementation_plan_yandex_search_registry_cleanup.md docs/artifacts/walkthrough_yandex_search_auth_fix.md docs/artifacts/walkthrough_yandex_search_registry_cleanup.md
```

```bash
sed -n '1,220p' .gitignore
sed -n '1,360p' docs/project_brief.md
```

## Tests Run

- no runtime tests in this milestone
- consistency check was done via targeted `rg` and file inspection

## Result

The PR branch now has the minimal planning and review artifacts needed for review, while production-like verification remains explicitly separate.
