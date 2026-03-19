# Production-Like Verification: Frontend Artist MVP Phase 2 Milestone 4 Yandex 403 Fix

Status: passed on `2026-03-19`.

## Newer Verified State On `2026-03-19`

Latest shared-docs production-like claims now come from `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_youtube_detail_refresh_unblock.md`, which verified that:

- `/jobs/{job_id}` reached `finished`
- both providers had `status="updated"`
- YouTube used `mode="entity_refresh"`
- Yandex used `mode="catalog_ingest"`
- `partial=false`
- post-sync `/artists/{id}` still had non-empty `yandex_catalog_sections`
- post-sync `/ui/artists/{id}` still showed `Yandex native catalog`

Historical note:

- the older `partial=true` Yandex-only payload preserved below remains valid evidence for the Yandex 403 fix milestone
- this artifact is intentionally not rewritten into the newer YouTube-unblocked result; it stays append-only for chronology

## Summary

- Goal: verify that the Yandex 403 fix unblocks the artist search -> artist overview -> sync -> jobs -> Yandex catalog refresh flow against PostgreSQL + Redis + worker with real provider tokens from `.env`.
- Scope: Yandex provider/catalog-ingest subsystem only.
- Outcome: passed.
- Acceptance result:
  - `/jobs/{job_id}` reached `finished`
  - terminal payload contained Yandex `status="updated"`, `mode="catalog_ingest"`, and `catalog_list_count=10`
  - terminal payload still included the expected failed YouTube result
  - post-sync `/artists/{id}` returned non-empty `yandex_catalog_sections`
  - post-sync `/ui/artists/{id}` rendered `Yandex native catalog`

## Effective Environment

- host API port: `8001`
- isolated PostgreSQL host port: `5433`
- isolated Redis host port: `6380`
- compose project: `netvrf-m4-yandex-403-fix`
- runtime env overrides:
  - `APP_ENV=staging`
  - `APP_DEBUG=false`
  - `APP_RELOAD=false`
  - `HEALTH_REQUIRE_REDIS=true`
  - `APP_PORT=8001`
  - `DATABASE_URL=postgresql+psycopg://netvrf:netvrf@localhost:5433/netvrf`
  - `REDIS_URL=redis://localhost:6380/0`
  - `PROVIDER_HTTP_TIMEOUT_SECONDS=15`
  - `SEARCH_PROVIDER_TIMEOUT_SECONDS=15`
  - `SYNC_PROVIDER_TIMEOUT_SECONDS=120`
- token handling:
  - real provider tokens were read from `.env` via `python-dotenv`
  - `.env` was not shell-sourced
  - tokens were not printed or logged

## Root Cause Confirmed During Live Debugging

- `GET /artists/218095` succeeded over the public route
- `GET /artists/218095/direct-albums` succeeded over the public route
- `GET /artists/218095/tracks` succeeded over the public route
- `GET /artists/218095/brief-info` returned `403 Forbidden` on both:
  - public request
  - authenticated retry with normalized `Authorization: OAuth <token>`

Final fix shape:

- keep public-first auth retry for Yandex catalog/detail routes
- normalize callback-style OAuth token values before authenticated retry
- treat `brief-info` as optional inside artist catalog ingest when it fails with `401` or `403`

## Commands Actually Run

Preflight:

```bash
.venv/bin/python -m pytest -q tests/providers/test_provider_clients.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py tests/api/test_sync_jobs.py
```

```bash
.venv/bin/ruff check app/providers/yandex_music/client.py app/services/yandex_catalog_service.py tests/providers/test_provider_clients.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py
```

Runtime setup:

```bash
/bin/zsh -lc "cat > /tmp/netvrf-m4-yandex-403-fix.override.yml <<'EOF'
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

API:

```bash
/bin/zsh -lc '.venv/bin/python - <<'"'"'PY'"'"'
import os
from dotenv import dotenv_values

values = dotenv_values(".env")
env = os.environ.copy()
for key in ("YOUTUBE_MUSIC_TOKEN", "YANDEX_MUSIC_TOKEN"):
    value = values.get(key)
    if value is not None:
        env[key] = value

env.update({
    "APP_ENV": "staging",
    "APP_DEBUG": "false",
    "APP_RELOAD": "false",
    "HEALTH_REQUIRE_REDIS": "true",
    "APP_PORT": "8001",
    "DATABASE_URL": "postgresql+psycopg://netvrf:netvrf@localhost:5433/netvrf",
    "REDIS_URL": "redis://localhost:6380/0",
    "PROVIDER_HTTP_TIMEOUT_SECONDS": "15",
    "SEARCH_PROVIDER_TIMEOUT_SECONDS": "15",
    "SYNC_PROVIDER_TIMEOUT_SECONDS": "120",
    "PYTHONUNBUFFERED": "1",
})
os.execvpe("./scripts/run_api.sh", ["./scripts/run_api.sh"], env)
PY'
```

Worker:

```bash
/bin/zsh -lc '.venv/bin/python - <<'"'"'PY'"'"'
import os
from dotenv import dotenv_values

values = dotenv_values(".env")
env = os.environ.copy()
for key in ("YOUTUBE_MUSIC_TOKEN", "YANDEX_MUSIC_TOKEN"):
    value = values.get(key)
    if value is not None:
        env[key] = value

env.update({
    "APP_ENV": "staging",
    "APP_DEBUG": "false",
    "APP_RELOAD": "false",
    "HEALTH_REQUIRE_REDIS": "true",
    "APP_PORT": "8001",
    "DATABASE_URL": "postgresql+psycopg://netvrf:netvrf@localhost:5433/netvrf",
    "REDIS_URL": "redis://localhost:6380/0",
    "PROVIDER_HTTP_TIMEOUT_SECONDS": "15",
    "SEARCH_PROVIDER_TIMEOUT_SECONDS": "15",
    "SYNC_PROVIDER_TIMEOUT_SECONDS": "120",
    "PYTHONUNBUFFERED": "1",
})
os.execvpe("/bin/sh", ["/bin/sh", "./scripts/run_worker.sh"], env)
PY'
```

Health probe:

```bash
curl -i http://127.0.0.1:8001/health
```

Live root-cause probe:

```bash
.venv/bin/python - <<'PY'
# load YANDEX_MUSIC_TOKEN from .env
# call get_artist_detail(), get_artist_brief_info(), get_artist_direct_albums(), get_artist_tracks()
# wrap urlopen to capture only URL + public/auth mode + status
PY
```

Final end-to-end verification:

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

Cleanup:

```bash
docker compose -p netvrf-m4-yandex-403-fix -f docker-compose.yml -f /tmp/netvrf-m4-yandex-403-fix.override.yml down -v
```

## Automated Preflight Results

- `.venv/bin/python -m pytest -q tests/providers/test_provider_clients.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py tests/api/test_sync_jobs.py`
  - `32 passed in 1.27s`
- `.venv/bin/ruff check app/providers/yandex_music/client.py app/services/yandex_catalog_service.py tests/providers/test_provider_clients.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py`
  - `All checks passed!`

## Live Verification Results

### Health

- `GET /health` returned `200`
- response payload:
  - `status=ok`
  - `database.status=ok`
  - `redis.status=ok`

### UI Artist Search -> Artist Overview

- query: `Krovostok`
- `GET /ui?q=Krovostok&kind=artist&limit=5` returned `200`
- canonical CTA present: `true`
- selected `artist_id`: `1`
- primary label: `Krovostok - Topic`

### Pre-Sync Artist State

For `artist_id=1`:

- `GET /artists/1`
  - returned `200`
  - linked Yandex `provider_id` was `218095`
  - `yandex_catalog_sections` count was `0`
  - `missing_on_yandex_view.total_items` was `0`
- `GET /ui/artists/1`
  - returned `200`
  - `Yandex native catalog` was not present in HTML

### Sync Enqueue And Worker Execution

- `POST /sync/artist/1`
  - returned `202`
  - `created=true`
  - job id: `773fb168-ded0-4927-9b7f-0205bc05260b`
  - initial status: `queued`

Observed job status transitions:

```json
["queued", "started", "finished"]
```

Worker output:

```text
03:21:46 default: app.tasks.sync_jobs.run_sync_job('773fb168-ded0-4927-9b7f-0205bc05260b') (...)
sync_provider_failed kind=artist target_id=1 provider=youtube error=NotImplementedError
03:21:58 default: Job OK (...)
03:21:58 Result is kept for 500 seconds
```

### Terminal Job Payload

`GET /jobs/773fb168-ded0-4927-9b7f-0205bc05260b` reached terminal state with:

```json
{
  "id": "773fb168-ded0-4927-9b7f-0205bc05260b",
  "kind": "artist",
  "target_id": "1",
  "status": "finished",
  "queue_name": "default",
  "attempts": 1,
  "payload_json": {
    "kind": "artist",
    "target_id": "1"
  },
  "result_json": {
    "kind": "artist",
    "target_id": "1",
    "updated_count": 1,
    "partial": true,
    "providers": [
      {
        "provider": "youtube",
        "provider_id": "UCi-dSgoZzJRuV5AWDkQi9zA",
        "status": "failed",
        "error": "YouTube Music provider integration is not implemented yet"
      },
      {
        "provider": "yandex",
        "provider_id": "218095",
        "status": "updated",
        "attempts": 1,
        "mode": "catalog_ingest",
        "catalog_artist_provider_id": "218095",
        "platform_artist_count": 12,
        "platform_release_count": 15,
        "platform_track_count": 147,
        "catalog_list_count": 10
      }
    ]
  },
  "error_json": null
}
```

### Post-Sync Artist State

After the finished job:

- `GET /artists/1`
  - returned `200`
  - `yandex_catalog_sections` count was `2`
  - section titles:
    - `Yandex direct albums`
    - `Adjacent artists on Yandex`
- `GET /ui/artists/1`
  - returned `200`
  - `Yandex native catalog` was present in HTML

## Final Verdict

- Yandex auth retry/token normalization: green
- Yandex artist ingest with forbidden `brief-info`: green
- `/health`: green
- `/ui` artist search -> artist overview: green
- pre-sync `/artists/{id}` and `/ui/artists/{id}`: green
- `POST /sync/artist/{id}` enqueue: green
- `/jobs/{job_id}` terminal state: green
- Yandex terminal payload acceptance: green
- post-sync Yandex catalog evidence in API and UI: green

This verification run satisfies the milestone acceptance criteria.
