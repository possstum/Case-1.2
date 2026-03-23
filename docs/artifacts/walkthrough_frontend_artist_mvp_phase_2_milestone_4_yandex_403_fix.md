# Walkthrough: Frontend Artist MVP Phase 2 Milestone 4 Yandex 403 Fix

Status: implemented and verified on `2026-03-19`.

## Goal

Unblock the live artist sync flow by fixing the Yandex catalog/detail request path so Yandex can complete `catalog_ingest` successfully even when YouTube `get_*()` still fails.

## Milestone 0: Plan Artifact

Changed files:

- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_4_yandex_403_fix.md`

Commands run:

- none

Tests run:

- none

## Milestone 1: Yandex Provider Auth Recovery

Changed files:

- `app/providers/yandex_music/client.py`
- `app/services/yandex_catalog_service.py`
- `tests/providers/test_provider_clients.py`
- `tests/services/test_sync_service.py`
- `tests/services/test_yandex_catalog_service.py`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_yandex_403_fix.md`

What changed:

- `YandexMusicClient` now normalizes callback-style OAuth token strings before building an auth header.
- Search remains public and unauthenticated.
- Yandex catalog/detail routes now try the public route first and retry once with `Authorization: OAuth <normalized token>` only on `401` or `403`.
- Live root-cause probing showed that `artists/{id}/brief-info` still returns `403` even after authenticated retry for `provider_id=218095`.
- `YandexCatalogIngestionService.ingest_artist()` now treats `brief-info` as optional when that endpoint fails with `401` or `403`, while still ingesting artist detail, direct albums, and artist tracks.
- Added provider client regression tests for:
  - public search staying unauthenticated
  - public `403` retrying with normalized OAuth
  - no-token `403` surfacing without retry
  - token normalization edge cases
- Added sync regression coverage proving that artist sync can finish with `partial=true` when YouTube fails and Yandex catalog ingest succeeds.
- Added catalog-ingest regression coverage proving that artist ingest still succeeds when Yandex `brief-info` is forbidden.

Commands run:

```bash
.venv/bin/python -m pytest -q tests/providers/test_provider_clients.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py tests/api/test_sync_jobs.py
```

```bash
.venv/bin/ruff check app/providers/yandex_music/client.py app/services/yandex_catalog_service.py tests/providers/test_provider_clients.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py
```

Tests run:

- `.venv/bin/python -m pytest -q tests/providers/test_provider_clients.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py tests/api/test_sync_jobs.py`
  - `32 passed in 1.27s`
- `.venv/bin/ruff check app/providers/yandex_music/client.py app/services/yandex_catalog_service.py tests/providers/test_provider_clients.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py`
  - `All checks passed!`

## Milestone 2: Production-Like Verification

Changed files:

- `docs/artifacts/production_like_verification.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_yandex_403_fix.md`

Commands run:

```bash
docker compose -p netvrf-m4-yandex-403-fix -f docker-compose.yml -f /tmp/netvrf-m4-yandex-403-fix.override.yml down -v
```

```bash
docker compose -p netvrf-m4-yandex-403-fix -f docker-compose.yml -f /tmp/netvrf-m4-yandex-403-fix.override.yml up -d postgres redis
```

```bash
docker compose -p netvrf-m4-yandex-403-fix -f docker-compose.yml -f /tmp/netvrf-m4-yandex-403-fix.override.yml exec -T postgres pg_isready -U netvrf -d netvrf
```

```bash
docker compose -p netvrf-m4-yandex-403-fix -f docker-compose.yml -f /tmp/netvrf-m4-yandex-403-fix.override.yml exec -T redis redis-cli ping
```

```bash
env APP_ENV=staging APP_DEBUG=false APP_RELOAD=false HEALTH_REQUIRE_REDIS=true APP_PORT=8001 DATABASE_URL=postgresql+psycopg://netvrf:netvrf@localhost:5433/netvrf REDIS_URL=redis://localhost:6380/0 PROVIDER_HTTP_TIMEOUT_SECONDS=15 SEARCH_PROVIDER_TIMEOUT_SECONDS=15 SYNC_PROVIDER_TIMEOUT_SECONDS=120 .venv/bin/alembic upgrade head
```

```bash
curl -i http://127.0.0.1:8001/health
```

```bash
.venv/bin/python - <<'PY'
# live probe of Yandex client methods with URL + public/auth mode capture only
PY
```

```bash
.venv/bin/python - <<'PY'
# GET /ui?q=Krovostok&kind=artist&limit=5
# GET /artists/{artist_id}
# GET /ui/artists/{artist_id}
# confirm linked yandex provider_id == 218095
# POST /sync/artist/{artist_id}
# poll /jobs/{job_id}
# GET /artists/{artist_id} after terminal state
# GET /ui/artists/{artist_id} after terminal state
PY
```

```bash
docker compose -p netvrf-m4-yandex-403-fix -f docker-compose.yml -f /tmp/netvrf-m4-yandex-403-fix.override.yml down -v
```

Tests run:

- production-like end-to-end verification against PostgreSQL `5433`, Redis `6380`, API `8001`, and worker with real provider tokens from `.env`

Verification result:

- selected canonical artist:
  - `artist_id=1`
  - label: `Krovostok - Topic`
  - linked Yandex `provider_id=218095`
- terminal job:
  - `job_id=773fb168-ded0-4927-9b7f-0205bc05260b`
  - observed statuses: `queued -> started -> finished`
- terminal payload:
  - Yandex `status="updated"`
  - Yandex `mode="catalog_ingest"`
  - Yandex `catalog_list_count=10`
  - `partial=true` because YouTube remained failed
- post-sync API:
  - `yandex_catalog_sections_count=2`
  - section titles: `Yandex direct albums`, `Adjacent artists on Yandex`
- post-sync UI:
  - `Yandex native catalog` rendered

Outcome:

- milestone acceptance is green
