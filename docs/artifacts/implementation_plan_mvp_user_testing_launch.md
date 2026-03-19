# Implementation Plan: MVP User Testing Launch

Status: updated on `2026-03-19`; Milestones 1-3 are complete on the current worktree and Milestone 4 scope is now frozen.

## Summary

- Goal: prepare NETvRF for a narrow first-user MVP launch without overstating live-provider readiness.
- Launch target: search-first MVP only.
- Current hard blocker: fix the observed search persistence race that can return `500` during concurrent cold-start `/search` and `/ui` requests for the same query.
- Rule for execution: one subsystem per milestone; do not widen scope until the previous milestone is green.

## Source Of Truth

- `docs/project_brief.md`
- `docs/artifacts/project_stage_status.md`
- `docs/artifacts/tomorrow_browser_demo_checklist.md`
- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/production_like_verification.md`

## Grounded Facts

- Local automated baseline is green on the current worktree:
  - `.venv/bin/ruff check .`
  - `.venv/bin/pytest -q tests/api`
  - `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core`
  - `.venv/bin/pytest -q`
- Runtime smoke is green for:
  - mounted API routes
  - temp-SQLite `404` / `429` / `503` paths
  - log redaction
- Staging-like host-run verification is partially green on the current worktree:
  - `GET /health` returned `200`
  - `GET /search?q=Motorama&kind=artist&limit=5` returned `200`
  - `GET /search?q=Krovostok&kind=artist&limit=5` returned `200`
  - `GET /ui` returned `200`
  - `GET /ui?q=Krovostok&kind=artist&limit=5` returned `200`
- One parallel cold-start probe produced a real runtime failure:
  - concurrent `GET /search?q=Motorama&kind=artist&limit=5`
  - concurrent `GET /ui?q=Motorama&kind=artist&limit=5`
  - `GET /ui` returned `500`
  - server log showed `IntegrityError` on unique constraint `uq_platform_artists_platform_platform_id`
- The failure is consistent with the current persistence shape:
  - `app/web/routes.py` calls `SearchService.search()` for `/ui`
  - `app/services/search_service.py` persists provider rows while merging results
  - `app/services/link_service.py` currently uses `select` plus `insert` plus `flush` without concurrent insert recovery
- The repository still has no tracked deployment workflow or public staging target.

## Launch Boundary

Safe scope for first-user MVP:

- `/ui`
- search flow
- artist-focused search queries with bounded claims
- known acceptable degraded states already documented in `README.md`

Out of scope for first-user MVP until separately re-verified:

- worker-backed sync
- `/jobs` as part of the user story
- generalized provider-quality claims
- production-readiness claims

## Milestones

### Milestone 0: Planning Bootstrap

Subsystem:

- planning artifacts only

Files:

- `docs/artifacts/implementation_plan_mvp_user_testing_launch.md`
- `docs/artifacts/walkthrough_mvp_user_testing_launch.md`

Edits:

- create the launch plan artifact first
- create a walkthrough artifact that records planning bootstrap and current blockers
- do not change application code in this milestone

Validation:

- `git status --short`
- `sed -n '1,220p' docs/artifacts/implementation_plan_mvp_user_testing_launch.md`
- `sed -n '1,220p' docs/artifacts/walkthrough_mvp_user_testing_launch.md`

Tests:

- none

### Milestone 1: Search Persistence Race Fix

Subsystem:

- search persistence

Files:

- `app/services/link_service.py`
- `tests/services/test_link_service.py`
- `tests/api/test_web_ui.py`
- `docs/artifacts/walkthrough_mvp_user_testing_launch.md`

Edits:

- make provider-row persistence safe when two requests try to persist the same provider entity concurrently
- keep the fix DB-compatible for both SQLite dev and PostgreSQL staging/prod
- prefer a compact fix local to persistence code instead of widening into unrelated search or web rendering logic
- add one regression test that proves duplicate provider-row persistence no longer fails the request path
- add one test that keeps `/ui` search green for the affected query shape under the fixed persistence path

Not allowed:

- no worker changes
- no sync changes
- no provider-client changes
- no docs churn outside the milestone walkthrough

Validation:

- `.venv/bin/ruff check app/services/link_service.py tests/services/test_link_service.py tests/api/test_web_ui.py`
- `.venv/bin/pytest -q tests/services/test_link_service.py tests/api/test_web_ui.py`
- `.venv/bin/pytest -q tests/api tests/services tests/providers tests/db tests/utils tests/core`

Runtime re-check after fix:

- bring up staging-like host-run API against isolated PostgreSQL + Redis
- re-run sequential `/search` and `/ui` probes for `Motorama`
- re-run a parallel cold-start probe for the same query
- acceptance: no `500`, no `IntegrityError`, stable `200` for `/search` and `/ui`

### Milestone 2: Search-First Launch Certification

Subsystem:

- runtime verification and demo bootstrap

Files:

- `scripts/reset_demo_env.sh`
- `scripts/run_demo_api.sh`
- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/walkthrough_mvp_user_testing_launch.md`

Edits:

- keep the clean reset/bootstrap flow one short command sequence
- verify a clean search-first environment for the certified query set
- certify `Krovostok` and `Motorama` as the initial search queries only if both remain stable on cold and warm requests
- do not widen into worker or sync if search-first baseline is already sufficient

Validation:

- `./scripts/reset_demo_env.sh`
- `./scripts/run_demo_api.sh`
- `curl -i http://127.0.0.1:8001/health`
- `curl -i 'http://127.0.0.1:8001/search?q=Krovostok&kind=artist&limit=5'`
- `curl -i 'http://127.0.0.1:8001/search?q=Motorama&kind=artist&limit=5'`
- `curl -i 'http://127.0.0.1:8001/ui?q=Krovostok&kind=artist&limit=5'`
- `curl -i 'http://127.0.0.1:8001/ui?q=Motorama&kind=artist&limit=5'`

Tests:

- targeted runtime probes only

### Milestone 3: User Testing Runbook And Scope Freeze

Subsystem:

- launch docs and operator runbook

Files:

- `README.md`
- `docs/project_brief.md`
- `docs/artifacts/project_stage_status.md`
- `docs/artifacts/tomorrow_browser_demo_checklist.md`
- `docs/artifacts/walkthrough_mvp_user_testing_launch.md`

Edits:

- align all user-facing launch docs to the same narrow claim boundary
- explicitly mark sync and jobs as out of scope for the first-user MVP unless re-certified later
- write the exact launch runbook:
  - reset command
  - app start command
  - browser URL
  - certified queries
  - acceptable degraded states
  - forbidden claims

Validation:

- `rg -n "production-ready|general live-provider|sync.*ready|jobs.*demo" README.md docs/project_brief.md docs/artifacts/project_stage_status.md docs/artifacts/tomorrow_browser_demo_checklist.md`
- manual doc review for consistency

Tests:

- none

### Milestone 4: User Access Gate

Subsystem:

- demo access path and operator handoff

Files:

- `docs/artifacts/implementation_plan_mvp_user_testing_launch.md`
- `docs/artifacts/walkthrough_mvp_user_testing_launch.md`
- `scripts/run_demo_api.sh`
- `README.md`
- `docs/project_brief.md`
- `docs/artifacts/runtime_verification.md`

Edits:

- compare three concrete access paths before choosing one:
  - operator laptop on trusted LAN/VPN with `DEMO_APP_HOST=0.0.0.0`
  - local demo app plus SSH reverse tunnel through an existing host
  - new temporary public VM/staging host
- choose the trusted LAN/VPN path as the first real tester path because it reuses the current demo scripts and avoids inventing a deploy target the repository does not have
- keep the first-tester story narrow:
  - browser URL is `http://<operator_lan_ip>:8001/ui`
  - certified queries remain `Motorama` and `Krovostok`
  - `/sync`, `/jobs`, worker-backed refresh, and public-internet access stay out of scope
- minimally extend `scripts/run_demo_api.sh` with optional `DEMO_ACCESS_HOST` output so the operator sees a shareable tester URL without printing secrets
- write a novice smoke runbook for private-network access and explicitly keep it limited to trusted LAN/VPN use

Validation:

- `sed -n '1,260p' docs/artifacts/implementation_plan_mvp_user_testing_launch.md`
- `sh -n scripts/run_demo_api.sh`
- `./scripts/reset_demo_env.sh`
- `DEMO_APP_HOST=0.0.0.0 DEMO_ACCESS_HOST=192.168.1.23 ./scripts/run_demo_api.sh`
- `curl -i http://127.0.0.1:8001/health`
- `curl -i 'http://127.0.0.1:8001/ui?q=Motorama&kind=artist&limit=5'`
- `curl -i 'http://127.0.0.1:8001/ui?q=Krovostok&kind=artist&limit=5'`

Tests:

- shell syntax check for the launcher
- local runtime smoke for `/health` and certified `/ui` queries in shared-bind mode
- manual second-device browser smoke to be executed by the operator on the same trusted LAN/VPN

## Acceptance Summary

The MVP is ready for first-user testing only when all statements below are true:

1. concurrent cold-start `/search` and `/ui` requests no longer fail with duplicate provider-row inserts
2. search-first staging-like runtime is green on the certified query set
3. launch docs all describe the same narrow MVP boundary
4. one concrete first-tester access path exists on a trusted LAN/VPN and has a documented smoke runbook

## Execution Rule

- Start with Milestone 1 only after this plan is reviewed.
- After Milestone 1 is implemented and verified, prepare Milestone 2 artifacts and commands before touching code for Milestone 2.
- If a new bug appears, fix it only if it belongs to the active milestone subsystem; otherwise record it and stop scope creep.
