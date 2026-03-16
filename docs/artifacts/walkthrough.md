# Walkthrough: Demo-Ready MVP Execution Log

Этот artifact фиксирует выполнение approved implementation plan по одному subsystem milestone за раз.

## Milestone 1: README Demo Runbook Alignment

Status: completed

Changed files:

- `README.md`

Commands run:

- `sh -n scripts/run_api.sh`
- `docker compose config`

Tests run:

- none

Notes:

- Replaced the stale health-only framing with the current verified MVP baseline.
- Grouped startup instructions into short copy-paste dev and staging-like runbooks.
- Added a demo route sequence, acceptable degraded behavior, the requested final smoke checklist, known limitations, and backup/restore smoke checklists.
- Kept the runbook environment-agnostic and did not introduce any new seed or demo data command.

## Milestone 2: Project Brief Truth Alignment

Status: completed

Changed files:

- `docs/project_brief.md`

Commands run:

- none

Tests run:

- none

Notes:

- Replaced the old dormant/not-wired summary with the current runtime truth from `app/main.py`, `app/api/router.py`, and the verified artifacts.
- Kept the brief focused on what is actually mounted, what is verified in the demo baseline, and what remains outside live-provider claims.
- Preserved the broad subsystem/model/service inventory, but removed outdated statements about missing settings, absent routers, and health-only runtime.

## Milestone 3: Verification Artifact Alignment

Status: completed

Changed files:

- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/walkthrough.md`
- `docs/artifacts/implementation_plan.md`

Commands run:

- `sh -n scripts/run_api.sh`
- `docker compose config`

Tests run:

- none

Notes:

- Refreshed `runtime_verification.md` to separate verified local baseline, verified staging-like PostgreSQL + Redis baseline, and unverified live-provider behavior.
- Kept all previously recorded exact runtime evidence and did not invent new live-provider results.
- Synced the on-disk implementation plan artifact to the approved docs-only scope.
- This pass changed documentation narrative only; no runtime code, provider logic, worker behavior, or DB schema was modified.

## Milestone 1: CI Workflow Closure

Status: completed

Changed files:

- `docs/artifacts/implementation_plan.md`
- `.github/workflows/ci.yml`

Commands run:

- `.venv/bin/python -m ruff check .`
- `.venv/bin/python -m pytest`

Tests run:

- `.venv/bin/python -m ruff check .`
- `.venv/bin/python -m pytest`

Notes:

- Tightened the workflow to the current verified local baseline instead of the earlier narrower command set.
- Kept Ruff as the first gate, now using `ruff check .`.
- Historical note: this interim plain-`pytest` baseline was later superseded by the split verified pytest baseline recorded in `Milestone 1: Split CI Workflow Baseline`.
- Kept image build and staging deploy out of CI because the repo still has no `Dockerfile` or deployment workflow/config.

## Milestone 2: CI Docs And Artifact Alignment

Status: completed

Changed files:

- `README.md`
- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/walkthrough.md`

Commands run:

- `.venv/bin/python -m ruff check .`
- `.venv/bin/python -m pytest`

Tests run:

- `.venv/bin/python -m ruff check .`
- `.venv/bin/python -m pytest`

Notes:

- Historical note: this docs entry reflected the interim plain-`pytest` CI baseline and was later superseded by the split verified baseline.
- Updated the README command table to the canonical `ruff check .` and `pytest` forms for that earlier closure.
- Recorded that image build is still omitted because there is no `Dockerfile`.
- Recorded that staging deploy is still omitted because the repo has no deployment workflow or approval gate.
- Refreshed the runtime verification artifact to the exact commands and results from this closure run.

## Milestone 1: Staging Config Surface

Status: completed

Changed files:

- `docs/artifacts/implementation_plan.md`
- `.env.staging.example`

Commands run:

- `docker compose config`

Tests run:

- none

Notes:

- Refreshed the `Implementation Plan` artifact to match the approved Postgres + Redis staging verification scope.
- Added `.env.staging.example` with Postgres and Redis defaults, while leaving `.env.example` on SQLite for normal local development.
- Confirmed the staging env sample matches the existing Compose credentials and published ports.

## Milestone 2: Non-Reload App Startup Path

Status: completed

Changed files:

- `scripts/run_api.sh`

Commands run:

- `chmod +x scripts/run_api.sh`
- `sh -n scripts/run_api.sh`

Tests run:

- `sh -n scripts/run_api.sh`

Notes:

- Added a launcher-only `APP_RELOAD` toggle.
- Default behavior remains reload-enabled for local development.
- `APP_RELOAD=false` now gives a staging-like host startup path without changing FastAPI settings or runtime wiring.
- Restored execute permission on `scripts/run_api.sh` so the README command form `./scripts/run_api.sh` works.

## Milestone 3: README Runbook And Smoke Checks

Status: completed

Changed files:

- `README.md`
- `docs/artifacts/implementation_plan.md`
- `docs/artifacts/walkthrough.md`

Commands run:

- `docker compose config`
- `sh -n scripts/run_api.sh`
- `.venv/bin/python -m pytest -q tests/db/test_migrations.py tests/db/test_schema_compile.py tests/api/test_health.py`
- `docker compose up -d postgres redis`
- `docker compose down`
- `docker ps --format '{{.ID}} {{.Image}} {{.Ports}} {{.Names}}'`
- `lsof -nP -iTCP:5432 -sTCP:LISTEN`
- `lsof -nP -iTCP:8000 -sTCP:LISTEN`
- `docker compose -p netvrf-staging-smoke -f /tmp/netvrf-staging-compose.yml up -d`
- `docker compose -p netvrf-staging-smoke -f /tmp/netvrf-staging-compose.yml exec postgres pg_isready -U netvrf -d netvrf`
- `docker compose -p netvrf-staging-smoke -f /tmp/netvrf-staging-compose.yml exec redis redis-cli ping`
- `/bin/zsh -lc 'set -a; . ./.env.staging.example; export DATABASE_URL=postgresql+psycopg://netvrf:netvrf@localhost:5433/netvrf; export REDIS_URL=redis://localhost:6380/0; set +a; .venv/bin/alembic upgrade head'`
- `/bin/zsh -lc 'set -a; . ./.env.staging.example; export DATABASE_URL=postgresql+psycopg://netvrf:netvrf@localhost:5433/netvrf; export REDIS_URL=redis://localhost:6380/0; export APP_PORT=8001; set +a; sh ./scripts/run_api.sh'`
- `curl -i http://127.0.0.1:8001/health`
- `curl -i 'http://127.0.0.1:8001/search?q=Motorama&kind=artist&limit=5'`
- `docker compose -p netvrf-staging-smoke -f /tmp/netvrf-staging-compose.yml exec postgres psql -U netvrf -d netvrf -c "select version_num from alembic_version;"`
- `docker compose -p netvrf-staging-smoke -f /tmp/netvrf-staging-compose.yml exec postgres psql -U netvrf -d netvrf -c "select tablename from pg_tables where schemaname='public' and tablename in ('artists','search_cache','sync_jobs') order by tablename;"`
- `docker compose -p netvrf-staging-smoke -f /tmp/netvrf-staging-compose.yml down`
- `/bin/zsh -lc 'set -a; . ./.env.staging.example; export DATABASE_URL=postgresql+psycopg://netvrf:netvrf@localhost:5433/netvrf; export REDIS_URL=redis://localhost:6380/0; export APP_PORT=8001; set +a; ./scripts/run_api.sh'`
- `curl -i http://127.0.0.1:8001/health`
- `docker compose -p netvrf-staging-smoke -f /tmp/netvrf-staging-compose.yml down`

Tests run:

- `sh -n scripts/run_api.sh`
- `.venv/bin/python -m pytest -q tests/db/test_migrations.py tests/db/test_schema_compile.py tests/api/test_health.py`
- manual Postgres + Redis smoke verification

Notes:

- Added the canonical staging verification runbook and expected results to `README.md`.
- Verified Alembic upgrade against PostgreSQL, `GET /health` returning `200`, `GET /search` returning the expected `503 search_providers_unavailable`, and the presence of `artists`, `search_cache`, and `sync_jobs`.
- The machine already had unrelated services bound to `5432`, `6379`, and `8000`, so the live smoke used a temporary standalone Compose file in `/tmp` on `5433`, `6380`, and `8001` without changing the repository runbook.
- After restoring the execute bit on `scripts/run_api.sh`, the exact README launcher form `./scripts/run_api.sh` was also verified end-to-end against the temporary Postgres + Redis stack.

## Milestone 1: Minimal CI Tooling Baseline

Status: completed

Changed files:

- `pyproject.toml`
- `app/db/models/canonical.py`
- `app/db/models/links.py`
- `app/db/models/platform.py`

Commands run:

- `.venv/bin/python -m pip install -e '.[dev]'`
- `.venv/bin/python -m ruff check app tests alembic`

Tests run:

- `python -m ruff check app tests alembic`

Notes:

- Added `ruff` as a dev dependency with a correctness-only rule set for the CI baseline.
- Fixed ORM forward-reference typing imports so the new lint step passes without changing runtime behavior.

## Milestone 2: GitHub Actions CI Workflow

Status: completed

Changed files:

- `.github/workflows/ci.yml`

Commands run:

- `.venv/bin/python - <<'PY' ... yaml.safe_load('.github/workflows/ci.yml') ... PY`

Tests run:

- local YAML parse/smoke of `.github/workflows/ci.yml`

Notes:

- Added a single GitHub Actions workflow with install, lint, and pytest steps for the verified local baseline.
- Historical note: this initial workflow shape was later narrowed to the split verified pytest baseline recorded below.
- Kept the workflow intentionally narrow: no service containers, no Python matrix, and no image build step.

## Milestone 3: CI Docs And Artifact Alignment

Status: completed

Changed files:

- `README.md`
- `docs/artifacts/implementation_plan.md`
- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/walkthrough.md`

Commands run:

- `.venv/bin/python -m ruff check app tests alembic`
- `.venv/bin/python -m pytest -q tests/api tests/services tests/providers tests/db tests/utils tests/core`

Tests run:

- `python -m ruff check app tests alembic`
- `python -m pytest -q tests/api tests/services tests/providers tests/db tests/utils tests/core`

Notes:

- Historical note: this entry captured the earlier single-bundle CI docs alignment and was later superseded by the split verified baseline.
- `README.md` now documents the canonical local-vs-CI command pairs for install, lint, and pytest for that earlier baseline.
- `docs/artifacts/runtime_verification.md` now records the exact CI-aligned local commands and results for that earlier baseline.
- `docs/artifacts/implementation_plan.md` was refreshed so the on-disk artifact matches the approved CI plan that was implemented.

## Docs-Only Hardening Runtime Verification Refresh

Status: completed

Changed files:

- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/walkthrough.md`

Commands run:

- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/api/test_web_ui.py`
- `.venv/bin/pytest -q tests/services tests/utils tests/providers tests/db`
- `.venv/bin/pytest -q tests/api tests/services tests/providers tests/db tests/utils tests/core`
- `.venv/bin/python - <<'PY' ... inspect create_app().routes for mounted API paths ... PY`
- `.venv/bin/python - <<'PY' ... create temp SQLite DB, run alembic upgrade head, smoke 404 / 503 / 429 and correlation-id echo ... PY`
- `.venv/bin/python - <<'PY' ... emit fake Authorization/Cookie/token through production log redaction pipeline ... PY`

Tests run:

- `tests/api`
- `tests/api/test_web_ui.py`
- `tests/services`
- `tests/utils`
- `tests/providers`
- `tests/db`
- `tests/api tests/services tests/providers tests/db tests/utils tests/core`

Notes:

- No code files changed in this refresh; only docs artifacts were updated.
- `docs/artifacts/runtime_verification.md` now reflects the actual post-hardening verified local baseline, including the final `52 passed` bundle and local smoke confirmation for `/search` and `/sync` rate limiting, `X-Correlation-ID`, and log redaction.

## Docs-Only Baseline Verification Refresh

Status: completed

Changed files:

- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/walkthrough.md`

Commands run:

- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/api/test_web_ui.py`
- `.venv/bin/pytest -q tests/services tests/utils tests/providers tests/db`
- `.venv/bin/pytest -q tests/services/test_sync_service.py::test_sync_service_refreshes_platform_rows_without_duplicates`
- `.venv/bin/python - <<'PY' ... inspect create_app().routes for mounted API paths ... PY`
- `.venv/bin/python - <<'PY' ... smoke `/artists/99999`, `/releases/99999`, `/tracks/99999`, `/search` with `ProviderRegistry(())` ... PY`

Tests run:

- `tests/api`
- `tests/api/test_web_ui.py`
- `tests/services`
- `tests/utils`
- `tests/providers`
- `tests/db`
- `tests/services/test_sync_service.py::test_sync_service_refreshes_platform_rows_without_duplicates`

Notes:

- `docs/artifacts/runtime_verification.md` now reflects the verified local baseline instead of the earlier search-only milestone report.
- The refresh keeps the no-provider `/search` wording exact: verified `503` for cold miss, with non-expired cache hits still documented as available baseline behavior.

## Docs-Only Correction Run

Status: completed

Changed files:

- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/walkthrough.md`

Notes:

- Runtime verification artifact created under `docs/artifacts/` to match existing artifact convention in this repository.
- The runtime verification document uses only checks actually executed in the previous run.
- Any claim without a directly executed check is marked there as `not verified`.

## Milestone 1: Database Schema Bootstrap

Status: completed

Changed files:

- `alembic/versions/7f6b4e2c9a11_application_schema_bootstrap.py`

Commands run:

- `.venv/bin/pytest -q tests/db/test_migrations.py`
- `tmp_db=$(mktemp /tmp/netvrf_migrate_copy.XXXXXX.db) && cp data/netvrf.db "$tmp_db" && DATABASE_URL="sqlite+pysqlite:///$tmp_db" .venv/bin/alembic upgrade head`

Tests run:

- `tests/db/test_migrations.py`

Notes:

- Added a forward schema revision after `4a5c6b7d8e9f`.
- Used metadata bootstrap instead of rewriting placeholder revisions.
- Verified upgrade against a stamped SQLite copy to avoid mutating the checked-in local DB directly.

## Milestone 2: Search Path Activation

Status: completed

Changed files:

- `app/core/config.py`
- `.env.example`
- `app/api/deps.py`
- `app/api/router.py`
- `app/providers/youtube_music/client.py`
- `app/providers/yandex_music/client.py`

Commands run:

- `.venv/bin/pytest -q tests/services/test_matching_config.py tests/api/test_search.py`
- `.venv/bin/python - <<'PY' ... print mounted /health and /search routes ... PY`
- `.venv/bin/python - <<'PY' ... GET /search without provider tokens ... PY`

Tests run:

- `tests/services/test_matching_config.py`
- `tests/api/test_search.py`

Notes:

- Added search-related settings defaults and env surface.
- Added search dependency factories, Redis-backed rate limiter, and no-op refresh scheduler.
- Mounted `/search` in the live API router.
- Default runtime without provider tokens now returns `503 search_providers_unavailable` instead of silent empty results.

## Milestone 3: Entity Detail API Activation

Status: completed

Changed files:

- `app/api/deps.py`
- `app/api/router.py`

Commands run:

- `.venv/bin/pytest -q tests/api/test_entities.py`
- `.venv/bin/python - <<'PY' ... print mounted health/search/detail routes ... PY`
- `.venv/bin/pytest -q tests/api/test_health.py tests/db/test_schema_compile.py tests/providers/test_provider_mappers.py tests/providers/test_provider_contracts.py tests/utils/test_normalization.py tests/utils/test_version_tags.py tests/services/test_matching_service.py tests/services/test_matching_config.py tests/db/test_migrations.py tests/api/test_search.py tests/api/test_entities.py`

Tests run:

- `tests/api/test_entities.py`
- final in-scope verification bundle:
  - `tests/api/test_health.py`
  - `tests/db/test_schema_compile.py`
  - `tests/providers/test_provider_mappers.py`
  - `tests/providers/test_provider_contracts.py`
  - `tests/utils/test_normalization.py`
  - `tests/utils/test_version_tags.py`
  - `tests/services/test_matching_service.py`
  - `tests/services/test_matching_config.py`
  - `tests/db/test_migrations.py`
  - `tests/api/test_search.py`
  - `tests/api/test_entities.py`

Notes:

- Added detail service factories and mounted `/artists/{artist_id}`, `/releases/{release_id}`, and `/tracks/{track_id}`.
- Added only the minimal shared sync scheduler export required for test helper imports.
- Sync/jobs/UI remain intentionally dormant.
- Final in-scope verification result: `27 passed`.

## Milestone 4: Sync/Jobs API Activation

Status: completed

Changed files:

- `app/api/deps.py`
- `app/tasks/queue.py`
- `app/services/sync_service.py`
- `app/api/router.py`
- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/walkthrough.md`

Commands run:

- `.venv/bin/pytest -q tests/api/test_sync_jobs.py`
- `.venv/bin/pytest -q tests/api/test_health.py tests/api/test_search.py tests/api/test_entities.py`
- `.venv/bin/python - <<'PY' ... print mounted health/search/entity/sync/jobs routes ... PY`
- `.venv/bin/python - <<'PY' ... override get_sync_job_scheduler to None and POST /sync/artist/{id} ... PY`

Tests run:

- `tests/api/test_sync_jobs.py`
- regression bundle:
  - `tests/api/test_health.py`
  - `tests/api/test_search.py`
  - `tests/api/test_entities.py`

Notes:

- Added sync-only dependency factories instead of reusing search provider availability guards.
- Added a minimal RQ-backed sync scheduler adapter that returns `rq_job_id` on success and `None` on enqueue/backend failure.
- Mounted `/sync/{kind}/{target_id}` and `/jobs/{job_id}` in the live API router.
- Fixed `SyncService` error mapping so unavailable scheduler/queue paths now return structured `503` responses instead of `500 TypeError`.
- Verified milestone result: `3 passed` in `tests/api/test_sync_jobs.py`, `10 passed` in the regression bundle.

## Milestone 5: Minimal Web UI Routing Slice

Status: completed

Changed files:

- `app/main.py`
- `app/api/deps.py`
- `app/web/routes.py`
- `app/web/render.py`
- `tests/test_support.py`
- `tests/api/test_web_ui.py`
- `docs/artifacts/implementation_plan.md`
- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/walkthrough.md`

Commands run:

- `.venv/bin/pytest -q tests/api/test_web_ui.py`
- `.venv/bin/pytest -q tests/api/test_health.py tests/api/test_search.py tests/api/test_entities.py`
- `.venv/bin/pytest -q tests/api/test_sync_jobs.py`
- `.venv/bin/python - <<'PY' ... print mounted /, /ui*, /static routes ... PY`
- `.venv/bin/python - <<'PY' ... GET /static/app.css via TestClient ... PY`

Tests run:

- `tests/api/test_web_ui.py`
- regression bundle:
  - `tests/api/test_health.py`
  - `tests/api/test_search.py`
  - `tests/api/test_entities.py`
  - `tests/api/test_sync_jobs.py`

Notes:

- Mounted the dormant `web_router` directly in `create_app()` and added `/static` serving for existing UI assets.
- Added a web-safe search dependency so `/ui` renders without configured providers while keeping JSON `/search` strict.
- Preserved existing sync/job behavior; the UI sync form still uses `SyncService.enqueue()` and redirects to `/ui/jobs/{job_id}`.
- Extended UI tests to cover root redirect, landing page, configured-provider search, provider-missing notice, artist page, sync redirect, and job page.
- Verified milestone result: `4 passed` in `tests/api/test_web_ui.py`, `10 passed` in the health/search/entity regression bundle, `3 passed` in the sync/jobs regression bundle.

## Milestone 6: Search Cache-First Contract Hardening

Status: completed

Changed files:

- `app/api/deps.py`
- `app/services/search_service.py`
- `tests/api/test_search.py`
- `docs/artifacts/implementation_plan.md`
- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/walkthrough.md`

Commands run:

- `.venv/bin/pytest -q tests/api/test_search.py`
- `.venv/bin/python - <<'PY' ... create temp SQLite DB, seed cache, GET /search for fresh/stale/miss without providers ... PY`
- `.venv/bin/pytest -q tests/api/test_health.py tests/api/test_entities.py tests/api/test_sync_jobs.py tests/api/test_web_ui.py`

Tests run:

- `tests/api/test_search.py`
- regression bundle:
  - `tests/api/test_health.py`
  - `tests/api/test_entities.py`
  - `tests/api/test_sync_jobs.py`
  - `tests/api/test_web_ui.py`

Notes:

- Changed JSON `/search` to build `SearchService` even when provider tokens are absent so the endpoint can serve non-expired cache entries before deciding whether live provider fan-out is possible.
- Added explicit no-provider runtime behavior: fresh/stale cache hits return `200`, while cold miss and expired cache return structured `503 search_providers_unavailable`.

## Milestone 1: Sync Rate Limiting Baseline

Status: completed

Changed files:

- `docs/artifacts/implementation_plan.md`
- `app/core/config.py`
- `app/api/deps.py`
- `app/api/routes/sync.py`
- `app/web/routes.py`
- `tests/test_support.py`
- `tests/api/test_sync_jobs.py`
- `tests/api/test_web_ui.py`
- `docs/artifacts/walkthrough.md`

Commands run:

- `.venv/bin/pytest -q tests/api/test_sync_jobs.py tests/api/test_web_ui.py`

Tests run:

- `tests/api/test_sync_jobs.py`
- `tests/api/test_web_ui.py`

Notes:

- Added `SYNC_RATE_LIMIT` and `SYNC_RATE_WINDOW_SECONDS` settings with defaults `5` and `60`.
- Added dedicated sync limiter wiring in `app/api/deps.py` while keeping the existing Redis-backed fixed-window, IP-keyed, fail-open behavior unchanged.
- Applied sync rate limiting to both `POST /sync/{kind}/{target_id}` and `POST /ui/sync/{kind}/{target_id}` so the UI path cannot bypass the API guard.
- Updated shared test client wiring so a single limiter override controls both search and sync rate-limit dependencies.
- Verified milestone result: `9 passed`.

## Milestone 2: Provider Timeout And Retry Policy

Status: completed

Changed files:

- `app/core/config.py`
- `app/api/deps.py`
- `app/tasks/sync_jobs.py`
- `app/providers/youtube_music/client.py`
- `app/providers/yandex_music/client.py`
- `app/services/search_service.py`
- `app/services/sync_service.py`
- `tests/api/test_search.py`
- `tests/services/test_sync_service.py`
- `tests/providers/test_provider_clients.py`
- `docs/artifacts/walkthrough.md`

Commands run:

- `.venv/bin/pytest -q tests/api/test_search.py tests/services/test_sync_service.py tests/providers/test_provider_clients.py`

Tests run:

- `tests/api/test_search.py`
- `tests/services/test_sync_service.py`
- `tests/providers/test_provider_clients.py`

Notes:

- Added explicit provider policy settings for client timeout, search retry attempts/backoff, and sync retry backoff.
- Removed hardcoded provider HTTP timeout values and now inject `PROVIDER_HTTP_TIMEOUT_SECONDS` from runtime settings into both API and worker provider construction.
- Added retry wrappers in `SearchService` and `SyncService` that stay behavior-preserving by default because all new retry/backoff settings default to one attempt and zero backoff.
- Added focused regressions for search retry, sync retry backoff, and provider client timeout propagation.
- Verified milestone result: `15 passed`.

## Milestone 3: Logging Redaction And Correlation-ID Coverage

Status: completed

Changed files:

- `app/core/logging.py`
- `tests/api/test_search.py`
- `tests/api/test_sync_jobs.py`
- `tests/core/test_logging.py`
- `docs/artifacts/walkthrough.md`

Commands run:

- `.venv/bin/pytest -q tests/api/test_search.py tests/api/test_sync_jobs.py tests/core/test_logging.py`

Tests run:

- `tests/api/test_search.py`
- `tests/api/test_sync_jobs.py`
- `tests/core/test_logging.py`

Notes:

- Hardened log redaction so nested dict/list/tuple payloads are sanitized recursively instead of only masking shallow string forms.
- Added explicit redaction coverage for header-style `Authorization`, `Cookie`, `Set-Cookie`, and token-like keys in both structured payloads and free-form strings.
- Kept the existing correlation-id middleware contract unchanged and added regression assertions that inbound `X-Correlation-ID` is echoed on both accepted and rate-limited `/sync` responses and on rate-limited `/search`.
- Verified milestone result: `16 passed`.

## Milestone 4: Docs Surface And Final Verification

Status: completed

Changed files:

- `.env.example`
- `README.md`
- `docs/artifacts/walkthrough.md`

Commands run:

- `.venv/bin/pytest -q tests/api tests/services tests/providers tests/db tests/utils tests/core`

Tests run:

- `tests/api`
- `tests/services`
- `tests/providers`
- `tests/db`
- `tests/utils`
- `tests/core`

Notes:

- Added the full security-baseline env surface to `.env.example`, including sync rate-limit settings, provider timeout policy, and retry/backoff controls.
- Added a concise README operations note for Redis-backed IP rate limits, provider timeout/retry settings, and secret handling expectations.
- Final verification bundle result after all milestones: `52 passed`.

## Milestone 1: Split CI Workflow Baseline

Status: completed

Changed files:

- `.github/workflows/ci.yml`
- `docs/artifacts/implementation_plan.md`
- `docs/artifacts/walkthrough.md`

Commands run:

- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/api/test_web_ui.py`
- `.venv/bin/pytest -q tests/services tests/utils tests/providers tests/db`
- `.venv/bin/pytest -q tests/api tests/services tests/providers tests/db tests/utils tests/core`

Tests run:

- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/api/test_web_ui.py`
- `.venv/bin/pytest -q tests/services tests/utils tests/providers tests/db`
- `.venv/bin/pytest -q tests/api tests/services tests/providers tests/db tests/utils tests/core`

Notes:

- Narrowed the existing GitHub Actions workflow in place instead of adding a second workflow.
- Switched the lint step to `ruff check .` and replaced the single pytest step with the four explicitly verified pytest commands.
- Kept CI intentionally narrow: no Docker image build, no service containers, no staging deploy, and no live-provider verification claims.
- Refreshed the `Implementation Plan` artifact so the on-disk plan matches the approved CI alignment scope.

## Milestone 2: CI Docs Baseline Alignment

Status: completed

Changed files:

- `README.md`
- `docs/project_brief.md`
- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/walkthrough.md`

Commands run:

- `rg -n "\\.venv/bin/python -m pytest|python -m pytest|Verified Local Vs CI Commands|python -m ruff check" README.md docs/project_brief.md docs/artifacts/runtime_verification.md`

Tests run:

- none; reused the verified milestone 1 command outputs

Notes:

- Replaced the stale single-`pytest` CI story in README, project brief, and runtime verification with the split verified baseline.
- Updated the local-versus-CI mapping to use `.venv/bin/ruff` and `.venv/bin/pytest` locally and `ruff` and `pytest` in CI.
- Recorded the current exact observed pass counts and timings for the verified lint/test commands while keeping live provider behavior explicitly unverified.

## Milestone 1: CI Pytest Deduplication

Status: completed

Changed files:

- `.github/workflows/ci.yml`
- `docs/artifacts/implementation_plan.md`

Commands run:

- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core`

Tests run:

- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core`

Notes:

- Reduced the workflow to the intended two pytest steps and kept `ruff check .` unchanged.
- `tests/api/test_web_ui.py` is now covered only through `tests/api`, so CI no longer runs it redundantly.

## Milestone 2: CI Baseline Docs Sync

Status: completed

Changed files:

- `README.md`
- `docs/project_brief.md`
- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/walkthrough.md`

Commands run:

- `rg -n "test_web_ui.py|pytest -q tests/api tests/services|pytest full baseline|web ui pytest baseline" README.md docs/project_brief.md docs/artifacts/runtime_verification.md .github/workflows/ci.yml`
- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core`

Tests run:

- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core`

Notes:

- Synced README, project brief, and runtime verification to the minimal two-command CI baseline.
- Kept the walkthrough append-only and left historical entries unchanged.
