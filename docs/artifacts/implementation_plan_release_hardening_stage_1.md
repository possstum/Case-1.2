# Implementation Plan: Release Hardening Stage 1

Status: prepared on `2026-03-20`.

## Summary

- Goal: close the immediate release-readiness gaps for exact branch `0e911d2fd123e472b2aa661fd06a8f2fac009747` without widening live-claim boundaries.
- Stage boundary:
  - add one deterministic seeded demo environment with fixed IDs
  - add one exact-branch verification artifact for the current SHA
  - re-run staging-like and production-like verification on this exact branch
- Out of scope:
  - public internet exposure
  - TLS termination
  - app-level auth
  - broader live-search certification beyond `Motorama` and `Krovostok`

## Source Of Truth

- `docs/project_brief.md`
- `docs/artifacts/project_stage_status.md`
- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/production_like_verification.md`
- `docs/artifacts/exact_branch_verification_2026_03_20.md`

## Grounded Starting Point

- branch: `yandex-catalog-ingest-pr`
- exact SHA: `0e911d2fd123e472b2aa661fd06a8f2fac009747`
- worktree status: clean
- diff shape versus `main`: large combined multi-subsystem branch diff
- local automated baseline:
  - `.venv/bin/ruff check .`
  - `.venv/bin/pytest -q`

## Stage 1 Milestones

### Milestone 1: Planning And Branch Freeze Artifact

Subsystem:

- docs/artifacts only

Files:

- `docs/artifacts/implementation_plan_release_hardening_stage_1.md`
- `docs/artifacts/walkthrough_release_hardening_stage_1.md`
- `docs/artifacts/exact_branch_verification_2026_03_20.md`
- `docs/artifacts/project_stage_status.md`

Edits:

- create Stage 1 plan and walkthrough artifacts
- create exact-branch verification artifact for the current SHA
- replace outdated dirty-worktree wording in `project_stage_status.md` with clean-branch-tip wording
- point release-readiness follow-up work at the exact-branch artifact

Validation:

- `git status -sb`
- `git rev-parse HEAD`
- `git diff --stat $(git merge-base HEAD main)..HEAD`
- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q`

Tests:

- baseline lint and full test suite only

### Milestone 2: Seeded Demo Bootstrap

Subsystem:

- demo bootstrap

Files:

- `app/demo/__init__.py`
- `app/demo/data.py`
- `app/demo/seed.py`
- `scripts/reset_seeded_demo_env.sh`
- `tests/test_support.py`
- `tests/demo/test_seed.py`
- `docs/artifacts/walkthrough_release_hardening_stage_1.md`

Edits:

- extract reusable synthetic demo seed data from test-only helpers
- add runtime-safe seed entrypoint `.venv/bin/python -m app.demo.seed`
- add deterministic seeded demo reset command
- keep all seeded provider IDs and URLs explicitly synthetic
- keep the current `./scripts/reset_demo_env.sh` semantics unchanged

Fixed identifiers:

- `artist_id=910001`
- `release_id=920001`
- `track_id=930001`
- `job_id=00000000-0000-4000-8000-000000910001`
- `rq_job_id=demo-rq-910001`

Validation:

- `.venv/bin/pytest -q tests/demo/test_seed.py tests/api/test_entities.py tests/api/test_web_ui.py tests/api/test_sync_jobs.py`
- `./scripts/reset_seeded_demo_env.sh`
- `DEMO_LOAD_DOTENV=0 ./scripts/run_demo_api.sh`
- `curl -i http://127.0.0.1:8001/health`
- `curl -i http://127.0.0.1:8001/artists/910001`
- `curl -i http://127.0.0.1:8001/releases/920001`
- `curl -i http://127.0.0.1:8001/tracks/930001`
- `curl -i http://127.0.0.1:8001/jobs/00000000-0000-4000-8000-000000910001`
- `curl -i http://127.0.0.1:8001/ui/artists/910001`
- `curl -i http://127.0.0.1:8001/ui/releases/920001`
- `curl -i http://127.0.0.1:8001/ui/tracks/930001`
- `curl -i http://127.0.0.1:8001/ui/jobs/00000000-0000-4000-8000-000000910001`

Tests:

- seed-specific automated coverage
- blank-token staging-like runtime smoke for seeded IDs

### Milestone 3: Staging-Like Exact Verification

Subsystem:

- verification/docs only

Files:

- `docs/artifacts/exact_branch_verification_2026_03_20.md`
- `docs/artifacts/walkthrough_release_hardening_stage_1.md`

Edits:

- record exact staging-like seeded verification commands and outcomes for this SHA
- keep one explicit blank-token `/search` probe so claim boundaries remain narrow

Validation:

- `./scripts/reset_seeded_demo_env.sh`
- `DEMO_LOAD_DOTENV=0 ./scripts/run_demo_api.sh`
- `curl -i http://127.0.0.1:8001/health`
- `curl -i http://127.0.0.1:8001/artists/910001`
- `curl -i http://127.0.0.1:8001/releases/920001`
- `curl -i http://127.0.0.1:8001/tracks/930001`
- `curl -i http://127.0.0.1:8001/jobs/00000000-0000-4000-8000-000000910001`
- `curl -i http://127.0.0.1:8001/ui/artists/910001`
- `curl -i http://127.0.0.1:8001/ui/releases/920001`
- `curl -i http://127.0.0.1:8001/ui/tracks/930001`
- `curl -i http://127.0.0.1:8001/ui/jobs/00000000-0000-4000-8000-000000910001`
- `curl -i 'http://127.0.0.1:8001/search?q=Motorama&kind=artist&limit=5'`

Tests:

- runtime probes only

### Milestone 4: Worker/Sync Readiness On The Exact Branch

Subsystem:

- worker/sync runtime

Files:

- `scripts/run_demo_worker.sh`
- `docs/artifacts/exact_branch_verification_2026_03_20.md`
- `docs/artifacts/production_like_verification.md`
- `docs/artifacts/walkthrough_release_hardening_stage_1.md`

Edits:

- add worker launcher that mirrors the demo API environment
- re-run exact-branch live sync verification for `Krovostok` and `Motorama`
- capture exact job IDs, exact terminal payloads, and exact post-sync evidence
- if live verification fails, document the failure as a current blocker instead of widening claims

Validation:

- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q`
- exact runtime command log in `docs/artifacts/exact_branch_verification_2026_03_20.md`

Tests:

- full suite before runtime work
- live production-like runtime probes for two artists if environment permits

## Milestone Exit Protocol

After each milestone, the walkthrough artifact must include:

- changed files
- commands run
- tests run
- acceptance result
- a paste-ready prompt for the next milestone

## Next-Stage Prompt Stub

`Реализуй Stage 2 deployability: добавь reproducible application Docker image for FastAPI web/api and RQ worker, затем добавь Render staging deployment automation from the exact verified branch, не расширяя scope в public internet access, TLS termination или app-level auth.`
