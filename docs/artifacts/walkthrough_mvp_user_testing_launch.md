# Walkthrough: MVP User Testing Launch

Status: milestones 0-4 recorded on `2026-03-19`.

## Goal

Prepare a narrow, honest launch path for first-user MVP testing without widening claims beyond the currently verified search-first surface.

## Scope

- `docs/artifacts/implementation_plan_mvp_user_testing_launch.md`
- `docs/artifacts/walkthrough_mvp_user_testing_launch.md`

Out of scope in this bootstrap slice:

- `app/*`
- `tests/*`
- `scripts/*`
- shared docs outside the new launch artifacts

## Milestone Log

### Milestone 0: Planning Bootstrap

Changed files:

- `docs/artifacts/implementation_plan_mvp_user_testing_launch.md`
- `docs/artifacts/walkthrough_mvp_user_testing_launch.md`

Commands run:

- `git status --short`
- `sed -n '1,220p' docs/project_brief.md`
- `sed -n '1,260p' docs/artifacts/project_stage_status.md`
- `sed -n '1,260p' docs/artifacts/runtime_verification.md`
- `sed -n '1,260p' README.md`
- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core`
- `.venv/bin/pytest -q`
- runtime route probe
- temp-SQLite smoke probe
- log redaction smoke probe
- staging-like host-run probes for `/health`, `/search`, and `/ui`

Tests run:

- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core`
- `.venv/bin/pytest -q`

Observed results:

- `ruff`: passed
- `tests/api`: `41 passed`
- `tests/services tests/providers tests/db tests/utils tests/core`: `58 passed`
- full suite: `105 passed`
- runtime smoke: green for route presence, temp-SQLite baseline, and log redaction
- staging-like host-run:
  - `/health` returned `200`
  - `/search?q=Motorama&kind=artist&limit=5` returned `200`
  - `/search?q=Krovostok&kind=artist&limit=5` returned `200`
  - `/ui` returned `200`
  - `/ui?q=Krovostok&kind=artist&limit=5` returned `200`

Runtime finding recorded for the next milestone:

- one parallel cold-start `Motorama` probe returned `500` on `/ui`
- server traceback showed `IntegrityError` on `uq_platform_artists_platform_platform_id`
- likely active area:
  - `app/web/routes.py`
  - `app/services/search_service.py`
  - `app/services/link_service.py`

Notes:

- this bootstrap created the Implementation Plan artifact first, per project instructions
- no runtime code changed in this slice
- the first implementation milestone is intentionally limited to the search persistence race

## Current Status

- Planning is ready.
- Milestone 1 and Milestone 2 are now completed on the current worktree.
- The next safe step is to freeze the user-testing scope and align launch docs to the same narrow search-first claim boundary.

### Milestone 1: Search Persistence Race Fix

Changed files:

- `app/services/link_service.py`
- `tests/services/test_link_service.py`
- `tests/api/test_web_ui.py`
- `docs/artifacts/walkthrough_mvp_user_testing_launch.md`

Commands run:

- `rg -n "begin_nested|IntegrityError|savepoint|on_conflict|rollback\\(" app tests`
- `sed -n '1,260p' app/services/link_service.py`
- `sed -n '1,260p' tests/api/test_web_ui.py`
- `.venv/bin/python - <<'PY' ... concurrent PlatformArtist insert repro on temp SQLite ... PY`
- `.venv/bin/ruff check app/services/link_service.py tests/services/test_link_service.py tests/api/test_web_ui.py`
- `.venv/bin/pytest -q tests/services/test_link_service.py tests/api/test_web_ui.py`
- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core`

Tests run:

- `.venv/bin/ruff check app/services/link_service.py tests/services/test_link_service.py tests/api/test_web_ui.py`
- `.venv/bin/pytest -q tests/services/test_link_service.py tests/api/test_web_ui.py`
- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core`

Observed results:

- targeted lint: passed
- targeted tests: `17 passed`
- API suite: `42 passed`
- non-API suite: `59 passed`

Implementation notes:

- moved provider-row creation to a local get-or-create helper with nested transaction recovery
- on concurrent duplicate insert, the request now re-reads the existing row instead of failing the whole request
- kept the fix local to `LinkService` so search, provider, worker, and sync logic stayed unchanged
- added a regression test that triggers a real duplicate insert race on SQLite via two sessions
- added a UI-level `Motorama` search regression to keep the affected web path covered

Milestone result:

- completed

### Milestone 4A: Access Path Decision And Artifact Freeze

Changed files:

- `docs/artifacts/implementation_plan_mvp_user_testing_launch.md`
- `docs/artifacts/walkthrough_mvp_user_testing_launch.md`

Commands run:

- `sed -n '1,280p' docs/artifacts/implementation_plan_mvp_user_testing_launch.md`
- `sed -n '1,320p' docs/artifacts/walkthrough_mvp_user_testing_launch.md`
- `sed -n '1,260p' docs/artifacts/runtime_verification.md`
- `sed -n '1,240p' scripts/run_demo_api.sh`
- `rg -n "Milestone 4|user-access|access path|demo|deploy|ngrok|tunnel|cloudflare|render|railway|localhost|APP_PORT|BASE_URL|public URL|tester|smoke" docs README.md app tests scripts`
- `command -v ssh`
- `command -v cloudflared`
- `command -v ngrok`
- `command -v tailscale`

Tests run:

- none

Observed results:

- the repository still has no `Dockerfile`, no deploy workflow, and no tracked staging/public host target
- the machine has `ssh` and `docker`, but no `cloudflared`, `ngrok`, or `tailscale`
- the existing web UI is server-rendered and route-relative, so it can be shared through one host/port without a separate frontend deployment step
- the chosen first real access path is operator-run demo API on a trusted LAN/VPN:
  - bind the app with `DEMO_APP_HOST=0.0.0.0`
  - share `http://<operator_lan_ip>:8001/ui`
  - keep the story limited to `Motorama` and `Krovostok`

Milestone result:

- completed

### Milestone 4B: Demo Launcher Hardening For LAN/VPN Sharing

Changed files:

- `scripts/run_demo_api.sh`
- `docs/artifacts/walkthrough_mvp_user_testing_launch.md`

Commands run:

- `sed -n '1,240p' scripts/run_demo_api.sh`
- `sh -n scripts/run_demo_api.sh`
- `./scripts/run_demo_api.sh`

Tests run:

- `sh -n scripts/run_demo_api.sh`
- default localhost launcher smoke

Observed results:

- added optional `DEMO_ACCESS_HOST` output without changing the existing launcher env contract
- default localhost startup text remains intact when `DEMO_ACCESS_HOST` is unset
- shared-bind startup now prints a tester-facing URL and a trusted-private-network warning when the bind host is non-loopback
- launcher output still does not print provider tokens or other secret env values

Milestone result:

- completed

### Milestone 4C: Novice Smoke Runbook And Scope Alignment

Changed files:

- `README.md`
- `docs/project_brief.md`
- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/walkthrough_mvp_user_testing_launch.md`

Commands run:

- `ipconfig getifaddr en0 || ipconfig getifaddr en1`
- `sed -n '1,220p' README.md`
- `sed -n '1,220p' docs/project_brief.md`
- `./scripts/reset_demo_env.sh`
- `DEMO_APP_HOST=0.0.0.0 DEMO_ACCESS_HOST=192.168.1.23 ./scripts/run_demo_api.sh`
- `curl -i http://127.0.0.1:8001/health`
- `curl -i 'http://127.0.0.1:8001/ui?q=Motorama&kind=artist&limit=5'`
- `curl -i 'http://127.0.0.1:8001/ui?q=Krovostok&kind=artist&limit=5'`

Tests run:

- local runtime smoke in shared-bind mode for `/health`
- local runtime smoke in shared-bind mode for `/ui?q=Motorama&kind=artist&limit=5`
- local runtime smoke in shared-bind mode for `/ui?q=Krovostok&kind=artist&limit=5`

Observed results:

- `ipconfig getifaddr en0 || ipconfig getifaddr en1` failed in this sandbox, so the runbook keeps it as an operator step and uses `<operator_lan_ip>` placeholders in docs
- clean demo reset completed before the shared-bind smoke
- shared-mode launcher printed both the bind URL and a sample shareable tester URL using `DEMO_ACCESS_HOST=192.168.1.23`
- `GET /health` returned `200` on `127.0.0.1:8001`
- `Motorama` and `Krovostok` UI probes both returned `200` in shared-bind mode
- second-device browser access on the same LAN/VPN remains a manual operator smoke step and is now explicitly documented as such

Milestone result:

- completed

### Milestone 3: User Testing Runbook And Scope Freeze

Changed files:

- `README.md`
- `docs/project_brief.md`
- `docs/artifacts/project_stage_status.md`
- `docs/artifacts/tomorrow_browser_demo_checklist.md`
- `docs/artifacts/walkthrough_mvp_user_testing_launch.md`

Commands run:

- `rg -n "Motorama|Krovostok|query set|search-first|sync|jobs|production-ready|live-provider|Worker-backed sync|certified|demo" README.md docs/project_brief.md docs/artifacts/project_stage_status.md docs/artifacts/tomorrow_browser_demo_checklist.md`
- `sed -n '1,260p' README.md`
- `sed -n '1,260p' docs/project_brief.md`
- `sed -n '1,260p' docs/artifacts/project_stage_status.md`
- `sed -n '1,260p' docs/artifacts/tomorrow_browser_demo_checklist.md`
- `.venv/bin/pytest -q`

Tests run:

- `.venv/bin/pytest -q`

Observed results:

- full suite after the milestone 1 race fix stayed green: `107 passed in 3.55s`
- README now carries an explicit first-user MVP scope and the certified query set
- project brief now includes the newer exact-query search-first certification boundary
- project stage status now reflects the fresh current-WIP search-first runtime artifact and updated test counts
- tomorrow checklist now includes the current certified state and the `Krovostok - Topic` presentation caveat

Milestone result:

- completed
- the original `IntegrityError` reproducer is no longer expected to fail the request path

### Milestone 2: Search-First Launch Certification

Changed files:

- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/walkthrough_mvp_user_testing_launch.md`

Commands run:

- `./scripts/reset_demo_env.sh`
- `./scripts/run_demo_api.sh`
- `curl -i http://127.0.0.1:8001/health`
- parallel cold-start probes:
  - `curl -i 'http://127.0.0.1:8001/search?q=Motorama&kind=artist&limit=5'`
  - `curl -i 'http://127.0.0.1:8001/ui?q=Motorama&kind=artist&limit=5'`
- warm `Motorama` probes:
  - `curl -i 'http://127.0.0.1:8001/search?q=Motorama&kind=artist&limit=5'`
  - `curl -i 'http://127.0.0.1:8001/ui?q=Motorama&kind=artist&limit=5'`
- cold `Krovostok` probes:
  - `curl -i 'http://127.0.0.1:8001/search?q=Krovostok&kind=artist&limit=5'`
  - `curl -i 'http://127.0.0.1:8001/ui?q=Krovostok&kind=artist&limit=5'`
- warm `Krovostok` probes:
  - `curl -i 'http://127.0.0.1:8001/search?q=Krovostok&kind=artist&limit=5'`
  - `curl -i 'http://127.0.0.1:8001/ui?q=Krovostok&kind=artist&limit=5'`
- `docker exec -i netvrf-demo-postgres-1 psql -U netvrf -d netvrf -At -F '|' -c "select 'platform_artists', count(*) from platform_artists union all select 'artists', count(*) from artists union all select 'search_cache', count(*) from search_cache order by 1;"`
- server-log poll from the running API session

Tests run:

- targeted runtime probes only

Observed results:

- clean reset succeeded
- `/health` returned `200`
- parallel cold-start `Motorama` `/search` and `/ui` both returned `200`
- server log showed only `200 OK` lines and no `IntegrityError`
- warm `Motorama` `/search` returned `cache.status="fresh"` and stable top `canonical_id=1`
- cold `Krovostok` `/search` returned `cache.status="miss"` and top `canonical_id=4`
- warm `Krovostok` `/search` returned `cache.status="fresh"` with the same top `canonical_id=4`
- both `Krovostok` UI probes returned `200`
- current clean-env DB snapshot after certification:
  - `artists|4`
  - `platform_artists|9`
  - `search_cache|1` after `Motorama`

Certification note:

- `Motorama` is a clean green launch query after the race fix
- `Krovostok` is also stable on cold and warm requests, but the current primary CTA label is `Krovostok - Topic`
- because of that label, the launch claim must stay narrow: certified query-specific search-first demo, not a blanket statement that all top labels are ideal

Milestone result:

- completed
