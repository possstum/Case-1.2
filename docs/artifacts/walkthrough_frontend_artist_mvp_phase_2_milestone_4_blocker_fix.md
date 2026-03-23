# Walkthrough: Frontend Artist MVP Phase 2 Milestone 4 Blocker Fix

Status: blocked on `2026-03-19`.

## Goal

Fix the Redis decode blocker in the queue/worker path, rerun the production-like artist sync verification against PostgreSQL + Redis + worker, and capture exact blocker evidence if the flow still fails.

## Changed Files

- `app/tasks/queue.py`
- `tests/tasks/test_queue.py`
- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_4_blocker_fix.md`
- `docs/artifacts/production_like_verification.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_blocker_fix.md`

## Code Change

- Updated the RQ Redis connection in `app/tasks/queue.py` to use `decode_responses=False`, keeping the queue API unchanged but making worker/job reads binary-safe for pickled RQ payloads.
- Added targeted regression tests for queue connection settings, queue wiring, scheduler enqueue behavior, and worker default queue wiring.

## Commands Run

```bash
.venv/bin/python -m pytest -q tests/tasks/test_queue.py tests/api/test_sync_jobs.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py
```

```bash
/bin/zsh -lc "cat > /tmp/netvrf-m4-blocker-fix.override.yml <<'EOF'
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
docker compose -p netvrf-m4-blocker-fix -f docker-compose.yml -f /tmp/netvrf-m4-blocker-fix.override.yml down -v
```

```bash
docker compose -p netvrf-m4-blocker-fix -f docker-compose.yml -f /tmp/netvrf-m4-blocker-fix.override.yml up -d postgres redis
```

```bash
docker compose -p netvrf-m4-blocker-fix -f docker-compose.yml -f /tmp/netvrf-m4-blocker-fix.override.yml exec -T postgres pg_isready -U netvrf -d netvrf
```

```bash
docker compose -p netvrf-m4-blocker-fix -f docker-compose.yml -f /tmp/netvrf-m4-blocker-fix.override.yml exec -T redis redis-cli ping
```

```bash
env APP_ENV=staging APP_DEBUG=false APP_RELOAD=false HEALTH_REQUIRE_REDIS=true APP_PORT=8001 DATABASE_URL=postgresql+psycopg://netvrf:netvrf@localhost:5433/netvrf REDIS_URL=redis://localhost:6380/0 PROVIDER_HTTP_TIMEOUT_SECONDS=15 SEARCH_PROVIDER_TIMEOUT_SECONDS=15 SYNC_PROVIDER_TIMEOUT_SECONDS=120 .venv/bin/alembic upgrade head
```

```bash
/bin/zsh -lc '.venv/bin/python - <<'"'"'PY'"'"'
# loads YOUTUBE_MUSIC_TOKEN and YANDEX_MUSIC_TOKEN from .env via python-dotenv
# sets APP_PORT=8001, DATABASE_URL=...:5433, REDIS_URL=...:6380/0
# then execs ./scripts/run_api.sh
PY'
```

```bash
/bin/zsh -lc '.venv/bin/python - <<'"'"'PY'"'"'
# loads YOUTUBE_MUSIC_TOKEN and YANDEX_MUSIC_TOKEN from .env via python-dotenv
# sets APP_PORT=8001, DATABASE_URL=...:5433, REDIS_URL=...:6380/0
# then execs /bin/sh ./scripts/run_worker.sh
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
PY
```

```bash
.venv/bin/python - <<'PY'
# final direct GET /jobs/4498d74c-af96-4368-a7bd-dadc4ee03a94
PY
```

```bash
kill 68013 68095
```

```bash
docker compose -p netvrf-m4-blocker-fix -f docker-compose.yml -f /tmp/netvrf-m4-blocker-fix.override.yml down -v
```

## Tests Run

- `.venv/bin/python -m pytest -q tests/tasks/test_queue.py tests/api/test_sync_jobs.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py`
  - `16 passed in 0.93s`

## Verification Results

- `/health` succeeded with `status=ok`, `database.status=ok`, and `redis.status=ok`.
- `/ui?q=Krovostok&kind=artist&limit=5` returned a valid canonical artist CTA.
- selected artist:
  - `artist_id=1`
  - primary label: `Krovostok - Topic`
- pre-sync `/artists/1` returned `200` with `yandex_catalog_sections_count=0`.
- pre-sync `/ui/artists/1` returned `200` and did not render `Yandex native catalog`.
- `POST /sync/artist/1` returned `202` and created job `4498d74c-af96-4368-a7bd-dadc4ee03a94`.
- worker evidence confirmed the queue decode blocker is fixed:
  - it dequeued `app.tasks.sync_jobs.run_sync_job('4498d74c-af96-4368-a7bd-dadc4ee03a94')`
- new blocker:
  - the RQ work-horse crashed on macOS fork safety with `+[NSCharacterSet initialize] ... fork() was called`
  - worker then logged `Moving job to FailedJobRegistry (Work-horse terminated unexpectedly; waitpid returned 6 (signal 6); )`
- `/jobs/4498d74c-af96-4368-a7bd-dadc4ee03a94` never left `status="queued"` in the app database view:
  - `attempts=0`
  - `started_at=null`
  - `finished_at=null`
  - `result_json=null`
  - `error_json=null`
- post-sync Yandex catalog proof was not reached.

## What Remains Unverified

- successful execution of `run_sync_job` inside the RQ work-horse
- `/jobs/{job_id}` terminal state handling in the production-like worker runtime
- Yandex provider `updated/catalog_ingest` terminal payload
- post-sync non-empty `yandex_catalog_sections`
- post-sync `Yandex native catalog` rendering on the artist page

## Result

This milestone removed the original Redis decoding blocker without widening the diff beyond queue/worker integration, but the live rerun exposed a new blocker in the worker work-horse path. The queue fix is valid, the milestone acceptance is still not green, and the next step should be a separate blocker-fix pass for the macOS fork-safety crash.
