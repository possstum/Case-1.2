# Walkthrough: Frontend Artist MVP Phase 2 Milestone 4

Status: blocked on `2026-03-19`.

## Goal

Run a production-like verification of the frontend artist flow against PostgreSQL + Redis + worker with the real provider tokens already present in `.env`, without widening scope into code fixes or stronger docs claims.

## Changed Files

- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_4.md`
- `docs/artifacts/production_like_verification.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4.md`

## Commands Run

```bash
.venv/bin/python -m pytest -q tests/api/test_health.py tests/api/test_search.py tests/api/test_entities.py tests/api/test_web_ui.py tests/api/test_sync_jobs.py
```

```bash
.venv/bin/python -m pytest -q tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py
```

```bash
docker compose -p netvrf-m4 -f docker-compose.yml -f /tmp/netvrf-m4.override.yml down -v
```

```bash
docker compose -p netvrf-m4 -f docker-compose.yml -f /tmp/netvrf-m4.override.yml up -d postgres redis
```

```bash
docker compose -p netvrf-m4 -f docker-compose.yml -f /tmp/netvrf-m4.override.yml exec -T postgres pg_isready -U netvrf -d netvrf
```

```bash
docker compose -p netvrf-m4 -f docker-compose.yml -f /tmp/netvrf-m4.override.yml exec -T redis redis-cli ping
```

```bash
env APP_ENV=staging APP_DEBUG=false APP_RELOAD=false HEALTH_REQUIRE_REDIS=true APP_PORT=8001 DATABASE_URL=postgresql+psycopg://netvrf:netvrf@localhost:5433/netvrf REDIS_URL=redis://localhost:6380/0 PROVIDER_HTTP_TIMEOUT_SECONDS=15 SEARCH_PROVIDER_TIMEOUT_SECONDS=15 SYNC_PROVIDER_TIMEOUT_SECONDS=120 .venv/bin/alembic upgrade head
```

```bash
env APP_ENV=staging APP_DEBUG=false APP_RELOAD=false HEALTH_REQUIRE_REDIS=true APP_PORT=8001 DATABASE_URL=postgresql+psycopg://netvrf:netvrf@localhost:5433/netvrf REDIS_URL=redis://localhost:6380/0 PROVIDER_HTTP_TIMEOUT_SECONDS=15 SEARCH_PROVIDER_TIMEOUT_SECONDS=15 SYNC_PROVIDER_TIMEOUT_SECONDS=120 ./scripts/run_api.sh
```

```bash
env APP_ENV=staging APP_DEBUG=false APP_RELOAD=false HEALTH_REQUIRE_REDIS=true APP_PORT=8001 DATABASE_URL=postgresql+psycopg://netvrf:netvrf@localhost:5433/netvrf REDIS_URL=redis://localhost:6380/0 PROVIDER_HTTP_TIMEOUT_SECONDS=15 SEARCH_PROVIDER_TIMEOUT_SECONDS=15 SYNC_PROVIDER_TIMEOUT_SECONDS=120 /bin/sh ./scripts/run_worker.sh
```

```bash
curl -i http://127.0.0.1:8001/health
```

```bash
.venv/bin/python - <<'PY'
# /ui ordered artist search probe
PY
```

```bash
.venv/bin/python - <<'PY'
# /artists/1 and /ui/artists/1 pre-sync probe
PY
```

```bash
.venv/bin/python - <<'PY'
# POST /sync/artist/1 plus /jobs polling
PY
```

```bash
.venv/bin/python - <<'PY'
# final /jobs/{job_id} direct probe
PY
```

```bash
docker compose -p netvrf-m4 -f docker-compose.yml -f /tmp/netvrf-m4.override.yml down -v
```

## Tests Run

- `.venv/bin/python -m pytest -q tests/api/test_health.py tests/api/test_search.py tests/api/test_entities.py tests/api/test_web_ui.py tests/api/test_sync_jobs.py`
  - `37 passed in 3.41s`
- `.venv/bin/python -m pytest -q tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py`
  - `8 passed in 0.98s`

## Live Verification Results

- `/health` succeeded with `status=ok`, `database.status=ok`, and `redis.status=ok`.
- `/ui?q=Krovostok&kind=artist&limit=5` produced the first valid canonical artist CTA.
- selected artist:
  - query: `Krovostok`
  - `artist_id=1`
  - primary label: `Krovostok - Topic`
- pre-sync `/artists/1` succeeded and already had a Yandex platform link, but `yandex_catalog_sections` was empty.
- pre-sync `/ui/artists/1` succeeded and did not render the `Yandex native catalog` section.
- `POST /sync/artist/1` returned `202` and created job `fbdf3c56-237c-431b-b8d1-e43f1b82202c`.
- repeated `/jobs/fbdf3c56-237c-431b-b8d1-e43f1b82202c` probes stayed at `status="queued"` with `attempts=0`.

## Blocker

The worker crashed before starting the queued job:

```text
UnicodeDecodeError: 'utf-8' codec can't decode byte 0x9c in position 1: invalid start byte
```

Likely root cause:

- RQ worker Redis access is built from `Redis.from_url(..., decode_responses=True)` in [`app/tasks/queue.py`](/Users/possstum/Documents/WorkID2/app/tasks/queue.py)
- the worker crashed while reading queued job data from Redis, which is consistent with binary job payload bytes being decoded as UTF-8

This is a blocker in the worker runtime path, not an acceptable provider-side degraded result.

## What Remains Unverified

- successful worker consumption of the queued sync job
- `queued -> started -> finished` transition on `/jobs/{job_id}`
- Yandex provider success payload with `mode="catalog_ingest"` and `catalog_list_count > 0`
- post-sync non-empty `yandex_catalog_sections` on `/artists/{id}`
- post-sync `Yandex native catalog` rendering on `/ui/artists/{id}`
- any live YouTube detail refresh success path

## Result

Milestone 4 did not complete green. The production-like run proved the health endpoint, live UI artist search, canonical artist overview selection, and pre-sync artist reads, but it exposed a worker/Redis decoding blocker before Yandex catalog refresh could execute.
