# Walkthrough: Frontend Artist MVP Phase 2 Milestone 4 Worker Execution Blocker Fix

Status: blocked on `2026-03-19`.

## Goal

Fix the local macOS worker execution blocker so the queued sync job actually runs, then rerun the full production-like artist sync verification and capture exact evidence for the next blocker.

## Changed Files

- `app/tasks/worker.py`
- `tests/tasks/test_queue.py`
- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_4_worker_execution_blocker_fix.md`
- `docs/artifacts/production_like_verification.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_worker_execution_blocker_fix.md`

## Code Change

- Updated [app/tasks/worker.py](/Users/possstum/Documents/WorkID2/app/tasks/worker.py) to select `rq.SimpleWorker` on macOS and keep standard `rq.Worker` elsewhere.
- Kept the queue names, Redis wiring, and worker entrypoint unchanged.
- Extended [tests/tasks/test_queue.py](/Users/possstum/Documents/WorkID2/tests/tasks/test_queue.py) with worker-class selection coverage for macOS and non-macOS.

## Commands Run

```bash
.venv/bin/python -m pytest -q tests/tasks/test_queue.py tests/api/test_sync_jobs.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py
```

```bash
/bin/zsh -lc "cat > /tmp/netvrf-m4-worker-fix.override.yml <<'EOF'
services:
  postgres:
    ports: !override
      - \"5433:5432\"
  redis:
    ports: !override
      - \"6380:6379\"
EOF"
```

```bash
docker compose -p netvrf-m4-worker-fix -f docker-compose.yml -f /tmp/netvrf-m4-worker-fix.override.yml down -v
```

```bash
docker compose -p netvrf-m4-worker-fix -f docker-compose.yml -f /tmp/netvrf-m4-worker-fix.override.yml up -d postgres redis
```

```bash
docker compose -p netvrf-m4-worker-fix -f docker-compose.yml -f /tmp/netvrf-m4-worker-fix.override.yml exec -T postgres pg_isready -U netvrf -d netvrf
```

```bash
docker compose -p netvrf-m4-worker-fix -f docker-compose.yml -f /tmp/netvrf-m4-worker-fix.override.yml exec -T redis redis-cli ping
```

```bash
env APP_ENV=staging APP_DEBUG=false APP_RELOAD=false HEALTH_REQUIRE_REDIS=true APP_PORT=8001 DATABASE_URL=postgresql+psycopg://netvrf:netvrf@localhost:5433/netvrf REDIS_URL=redis://localhost:6380/0 PROVIDER_HTTP_TIMEOUT_SECONDS=15 SEARCH_PROVIDER_TIMEOUT_SECONDS=15 SYNC_PROVIDER_TIMEOUT_SECONDS=120 .venv/bin/alembic upgrade head
```

```bash
/bin/zsh -lc '.venv/bin/python - <<'"'"'PY'"'"'
# loads provider tokens from .env via python-dotenv
# then execs ./scripts/run_api.sh with APP_PORT=8001, DATABASE_URL=:5433, REDIS_URL=:6380
PY'
```

```bash
/bin/zsh -lc '.venv/bin/python - <<'"'"'PY'"'"'
# loads provider tokens from .env via python-dotenv
# then execs /bin/sh ./scripts/run_worker.sh with APP_PORT=8001, DATABASE_URL=:5433, REDIS_URL=:6380
PY'
```

```bash
curl -i http://127.0.0.1:8001/health
```

```bash
.venv/bin/python - <<'PY'
# GET /ui?q=Krovostok&kind=artist&limit=5
# GET /artists/{id}
# GET /ui/artists/{id}
# POST /sync/artist/{id}
# poll /jobs/{job_id}
# GET /artists/{id} after terminal state
# GET /ui/artists/{id} after terminal state
PY
```

```bash
kill 69222 69217
```

```bash
docker compose -p netvrf-m4-worker-fix -f docker-compose.yml -f /tmp/netvrf-m4-worker-fix.override.yml down -v
```

## Tests Run

- `.venv/bin/python -m pytest -q tests/tasks/test_queue.py tests/api/test_sync_jobs.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py`
  - `18 passed in 0.89s`

## Verification Results

- `/health` succeeded with `status=ok`, `database.status=ok`, and `redis.status=ok`.
- `/ui?q=Krovostok&kind=artist&limit=5` returned a valid canonical artist CTA.
- selected artist:
  - `artist_id=1`
  - primary label: `Krovostok - Topic`
- pre-sync `/artists/1` returned `200` with `yandex_catalog_sections_count=0`.
- pre-sync `/ui/artists/1` returned `200` and did not render `Yandex native catalog`.
- `POST /sync/artist/1` returned `202` and created job `ae8a9bd7-2562-4d7d-877a-23c30870fbef`.
- worker execution is now real:
  - it ran `app.tasks.sync_jobs.run_sync_job('ae8a9bd7-2562-4d7d-877a-23c30870fbef')`
  - `/jobs/{job_id}` transitioned `queued -> failed`
  - `attempts=1`
  - `started_at` and `finished_at` were both populated
- new blocker is provider refresh:
  - YouTube provider failed because `get_*()` is still not implemented
  - Yandex provider failed with `HTTP Error 403: Forbidden`
- terminal job payload carried `error_json.reason="provider_refresh_failed"` instead of a successful Yandex `updated/catalog_ingest` result.
- post-terminal `/artists/1` did show one Yandex-native section:
  - `Adjacent artists on Yandex`
- post-terminal `/ui/artists/1` did render `Yandex native catalog`, but this was still not the accepted success condition.

## What Remains Unverified

- Yandex successful live catalog ingest for artist sync
- terminal payload with `provider="yandex"`, `status="updated"`, `mode="catalog_ingest"`, and `catalog_list_count > 0`
- post-sync direct Yandex catalog sections beyond the observed adjacent-artists section
- any successful live YouTube detail refresh path

## Result

This milestone fixed the worker execution subsystem and removed the local macOS blocker. The frontend artist sync flow now advances through queueing, worker execution, and terminal job persistence. The next blocker is now the real product blocker: Yandex live provider refresh is returning `403`, while YouTube detail refresh remains stubbed.
