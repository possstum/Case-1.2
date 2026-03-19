# Walkthrough: Frontend Artist MVP Phase 2 Milestone 4 YouTube Detail Refresh Unblock

Status: passed on `2026-03-19`.

## Goal

Unblock the remaining live artist sync follow-up by implementing YouTube detail refresh so the terminal sync payload can reach `partial=false` while preserving the already-verified Yandex catalog ingest path.

## Scope

- `app/providers/youtube_music/client.py`
- `tests/providers/test_provider_clients.py`
- `tests/services/test_sync_service.py`
- milestone artifacts only

Out of scope:

- Yandex subsystem changes
- frontend copy or rendering changes
- queue/worker subsystem changes
- shared docs claims outside this milestone artifact

## Dirty-Worktree Note

Before this milestone started, the worktree already contained unrelated or prior-milestone changes, including edits in:

- `tests/providers/test_provider_clients.py`
- `tests/services/test_sync_service.py`
- multiple Yandex, worker, web, and artifact files outside this milestone scope

This follow-up must edit only the YouTube provider client, the targeted test files above, and these new milestone artifacts.

## Pre-Edit Probe

Commands run:

```bash
.venv/bin/python - <<'PY'
# load YOUTUBE_MUSIC_TOKEN from .env via dotenv_values
# call channels.list, playlists.list, videos.list
# print only endpoint name, redacted params, status, items_len, and response keys
PY
```

Observed safe probe summary:

- `channels.list` for `UCi-dSgoZzJRuV5AWDkQi9zA`: `200`, `items_len=1`, item keys included `snippet`
- `videos.list` sample probe: `200`, `items_len=1`, item keys included `snippet` and `contentDetails.duration`
- `playlists.list` with a dummy id: `200`, `items_len=0`

Implementation implication:

- live shape confirms the minimal artist and track mappings
- release mapping will stay limited to the documented `playlists.list` fields and be locked with targeted tests

## Milestone Log

### Milestone 0: Artifact Bootstrap

Changed files:

- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_4_youtube_detail_refresh_unblock.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_youtube_detail_refresh_unblock.md`

Commands run:

- pre-edit YouTube probe command above

Tests run:

- none

Notes:

- artifact paths were created before code edits
- `docs/artifacts/production_like_verification.md` will remain untouched

### Milestone 1: YouTube Provider Detail Refresh

Changed files:

- `app/providers/youtube_music/client.py`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_youtube_detail_refresh_unblock.md`

Commands run:

- no separate commands beyond the pre-edit probe

Tests run:

- none

Notes:

- replaced the single search endpoint constant with dedicated `search`, `channels`, `playlists`, and `videos` endpoints
- added one shared helper that validates Google `items[]` responses and raises `ValueError` for missing entities
- implemented conservative detail mappings for artist, release, and track refresh
- kept unknown YouTube fields such as `release_type`, `release_title`, and `track_number` as `None`

### Milestone 2: Targeted Regression Tests

Changed files:

- `tests/providers/test_provider_clients.py`
- `tests/services/test_sync_service.py`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_youtube_detail_refresh_unblock.md`

Commands run:

```bash
.venv/bin/python -m pytest -q tests/providers/test_provider_clients.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py tests/api/test_sync_jobs.py
```

```bash
.venv/bin/ruff check app/providers/youtube_music/client.py tests/providers/test_provider_clients.py tests/services/test_sync_service.py
```

Tests run:

- `.venv/bin/python -m pytest -q tests/providers/test_provider_clients.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py tests/api/test_sync_jobs.py`
  - `39 passed in 1.06s`
- `ruff check`
  - `All checks passed!`

Notes:

- added success-path provider tests for `get_artist()`, `get_release()`, and `get_track()`
- added a regression that empty `items[]` raises `ValueError` across all three detail methods
- added duration coverage for both valid and malformed YouTube `contentDetails.duration`
- extended the full-success artist sync contract to assert `partial is False` and `status="updated"` for both providers

### Milestone 3: Production-Like Verification

Changed files:

- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_youtube_detail_refresh_unblock.md`

Commands run:

```bash
cat > /tmp/netvrf-m4-youtube.override.yml <<'EOF'
services:
  postgres:
    ports: !override
      - "5433:5432"
  redis:
    ports: !override
      - "6380:6379"
EOF
```

```bash
docker compose -p netvrf-m4-youtube -f docker-compose.yml -f /tmp/netvrf-m4-youtube.override.yml down -v
```

```bash
docker compose -p netvrf-m4-youtube -f docker-compose.yml -f /tmp/netvrf-m4-youtube.override.yml up -d postgres redis
```

```bash
docker compose -p netvrf-m4-youtube -f docker-compose.yml -f /tmp/netvrf-m4-youtube.override.yml exec -T postgres pg_isready -U netvrf -d netvrf
```

```bash
docker compose -p netvrf-m4-youtube -f docker-compose.yml -f /tmp/netvrf-m4-youtube.override.yml exec -T redis redis-cli ping
```

```bash
env APP_ENV=staging APP_DEBUG=false APP_RELOAD=false HEALTH_REQUIRE_REDIS=true APP_PORT=8001 DATABASE_URL=postgresql+psycopg://netvrf:netvrf@localhost:5433/netvrf REDIS_URL=redis://localhost:6380/0 PROVIDER_HTTP_TIMEOUT_SECONDS=15 SEARCH_PROVIDER_TIMEOUT_SECONDS=15 SYNC_PROVIDER_TIMEOUT_SECONDS=120 .venv/bin/alembic upgrade head
```

```bash
/bin/zsh -lc '.venv/bin/python - <<'"'"'PY'"'"'
# loads YOUTUBE_MUSIC_TOKEN and YANDEX_MUSIC_TOKEN from .env via dotenv_values
# execs ./scripts/run_api.sh with APP_PORT=8001, PostgreSQL 5433, Redis 6380
PY'
```

```bash
/bin/zsh -lc '.venv/bin/python - <<'"'"'PY'"'"'
# loads YOUTUBE_MUSIC_TOKEN and YANDEX_MUSIC_TOKEN from .env via dotenv_values
# execs ./scripts/run_worker.sh with the same staging-like env
PY'
```

```bash
curl -i http://127.0.0.1:8001/health
```

```bash
.venv/bin/python - <<'PY'
# GET /ui?q=Krovostok&kind=artist&limit=5
# GET /artists/{artist_id}
# GET /ui/artists/{artist_id}
# confirm yandex provider_id == 218095 and youtube provider_id == UCi-dSgoZzJRuV5AWDkQi9zA
# POST /sync/artist/{artist_id}
# poll /jobs/{job_id}
# GET /artists/{artist_id} and /ui/artists/{artist_id} after terminal state
PY
```

```bash
docker compose -p netvrf-m4-youtube -f docker-compose.yml -f /tmp/netvrf-m4-youtube.override.yml down -v
```

Tests run:

- none beyond the already-green targeted automated bundle above

## Live Verification Results

- `/health` returned `200` with `status=ok`, `database.status=ok`, and `redis.status=ok`
- `GET /ui?q=Krovostok&kind=artist&limit=5` selected canonical `artist_id=1`
- provider-id gate passed:
  - YouTube `provider_id=UCi-dSgoZzJRuV5AWDkQi9zA`
  - Yandex `provider_id=218095`
- pre-sync `GET /artists/1` returned `yandex_catalog_sections_count=0`
- pre-sync `GET /ui/artists/1` did not include `Yandex native catalog`
- `POST /sync/artist/1` returned `202` and created job `6fbd6af1-a396-4a1a-87a6-713707640129`
- observed job status transitions:
  - `queued`
  - `started`
  - `finished`
- worker output stayed clean:
  - `app.tasks.sync_jobs.run_sync_job('6fbd6af1-a396-4a1a-87a6-713707640129')`
  - `Job OK`

Terminal payload:

```json
{
  "kind": "artist",
  "target_id": "1",
  "updated_count": 2,
  "partial": false,
  "providers": [
    {
      "provider": "youtube",
      "provider_id": "UCi-dSgoZzJRuV5AWDkQi9zA",
      "status": "updated",
      "attempts": 1,
      "mode": "entity_refresh"
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
}
```

Post-sync state:

- `GET /artists/1` returned `yandex_catalog_sections_count=2`
- `GET /ui/artists/1` included `Yandex native catalog`

## Final Verdict

- YouTube detail refresh unblock: green
- targeted regression bundle: green
- production-like artist sync on PostgreSQL + Redis + worker: green
- terminal payload acceptance:
  - both providers `status="updated"`: green
  - YouTube `mode="entity_refresh"`: green
  - Yandex `mode="catalog_ingest"` with `catalog_list_count > 0`: green
  - `partial=false`: green
- no regression in Yandex live sync path was observed
