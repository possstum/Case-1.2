# Walkthrough: Merge-Ready PR Milestone 1

Status: completed on `2026-03-19`.

## Goal

Isolate the current Yandex catalog ingest work into a dedicated PR branch and remove out-of-scope changes from the review diff.

## What Changed

- created feature branch `yandex-catalog-ingest-pr`
- added `docs/artifacts/implementation_plan_merge_ready_pr.md`
- stashed out-of-scope changes under `stash@{0}` with message `out-of-scope-for-yandex-catalog-pr`

## Changed Files In This Milestone

- `docs/artifacts/implementation_plan_merge_ready_pr.md`

## Commands Run

```bash
git switch -c yandex-catalog-ingest-pr
```

```bash
git stash push -u -m 'out-of-scope-for-yandex-catalog-pr' -- README.md docs/artifacts/runtime_verification.md docs/artifacts/implementation_plan.md docs/artifacts/walkthrough.md docs/artifacts/manual_verification_checklist.md app/demo tests/api/test_demo_routes.py tests/db/test_demo_loader.py .env.save netvrf.egg-info/PKG-INFO netvrf.egg-info/SOURCES.txt
```

```bash
git status --short --branch
git stash list --max-count=2
```

## Tests Run

- no tests were needed for this milestone; this milestone only changed branch hygiene and PR scope isolation

## Result

The branch now contains only the intended Yandex catalog ingest review unit plus the new merge-ready planning artifact.
