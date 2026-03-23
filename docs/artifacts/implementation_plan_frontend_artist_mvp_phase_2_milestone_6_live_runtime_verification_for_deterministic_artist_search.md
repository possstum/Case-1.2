# Implementation Plan: Frontend Artist MVP Phase 2 Milestone 6 Live Runtime Verification For Deterministic Artist Search

Status: executed and blocked on `2026-03-19` at runtime preconditions.

## Summary

- Goal: live-verify that deterministic `artist` search keeps the top canonical result stable for `Krovostok` and `Motorama` on cold and warm `/search?q=...&kind=artist&limit=5`.
- Scope: search subsystem verification and milestone artifacts only.
- Out of scope:
  - worker, queue, sync, Yandex subsystem, artist detail pages, frontend runtime code
  - unrelated dirty files
  - shared docs and historical milestone artifacts

## Source Of Truth

- `docs/project_brief.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_youtube_detail_refresh_unblock.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_docs_alignment_after_youtube_detail_refresh_unblock.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`

## Grounded Facts

- `app/services/search_service.py` already emits `features_json.search_rank_version="artist_query_v1"` for artist queries.
- `tests/api/test_search.py` already has targeted automated coverage for deterministic artist ranking.
- `.env` contains both provider tokens, but token values must never be printed or logged.
- Local defaults are SQLite plus `redis://localhost:6379/0`.
- `data/netvrf.db` exists and currently has no `search:v2:artist:5:krovostok` or `search:v2:artist:5:motorama` rows.
- No local API is listening on `127.0.0.1:8000` or `127.0.0.1:8001`.
- If local Redis is unavailable, only repo-local Redis may be started. Worker must stay stopped.
- Live verification must use isolated temp SQLite state if a new API runtime is started.

## Public Interface Impact

- Expected green path: no API schema changes.
- If live verification reveals a search-only defect, only `app/services/search_service.py`, `tests/api/test_search.py`, and milestone 6 artifacts may change.
- If a search-only fix changes cached artist ordering or `search_rank_*` semantics, bump the search cache version to avoid stale ordering.

## Milestones

### Milestone 0: Artifact Bootstrap

Create first:

- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_6_live_runtime_verification_for_deterministic_artist_search.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_6_live_runtime_verification_for_deterministic_artist_search.md`

Record:

- dirty-worktree scope from `git status --short`

### Milestone 1: Read-Only Preflight

Run only non-mutating probes:

```bash
git status --short
awk -F= '...' .env
curl -sS -i http://127.0.0.1:8000/health
curl -sS -i http://127.0.0.1:8001/health
sqlite3 data/netvrf.db "select cache_key from search_cache where cache_key in ('search:v2:artist:5:krovostok','search:v2:artist:5:motorama');"
docker ps --format '{{.Names}}\t{{.Ports}}'
```

Decision rules:

- reuse an already-running API only if cold and warm behavior can still be proven
- otherwise prefer isolated API-only runtime on temp SQLite
- reuse `localhost:6379` only if it is reachable
- if Redis is unavailable, start only repo-local Redis
- if `6379` remains blocked or unreachable, stop and document blocker without widening scope

### Milestone 2: Minimal Runtime Bring-Up

Use temp DB:

- `/tmp/netvrf_m6_deterministic_artist_search.db`

Start only what is needed:

```bash
docker compose up -d redis
docker compose exec -T redis redis-cli ping
DATABASE_URL=sqlite+pysqlite:////tmp/netvrf_m6_deterministic_artist_search.db REDIS_URL=redis://localhost:6379/0 .venv/bin/alembic upgrade head
/bin/zsh -lc 'set -a; . ./.env; export APP_PORT=8001 APP_RELOAD=false HEALTH_REQUIRE_REDIS=true DATABASE_URL=sqlite+pysqlite:////tmp/netvrf_m6_deterministic_artist_search.db REDIS_URL=redis://localhost:6379/0 PROVIDER_HTTP_TIMEOUT_SECONDS=15 SEARCH_PROVIDER_TIMEOUT_SECONDS=15; set +a; ./scripts/run_api.sh'
curl -sS -i http://127.0.0.1:8001/health
```

Requirements:

- `/health` must return `200`
- database and redis status must both be healthy
- worker must remain stopped

### Milestone 3: Live Verification

Hit only `/search`, twice per query, and print only safe fields:

- `query`
- request index
- `cache.status`
- top `kind`
- top `canonical_id`
- top youtube and yandex `provider_id`
- `search_rank_version`
- `partial`
- `missing_platforms`

Queries:

- `/search?q=Krovostok&kind=artist&limit=5`
- `/search?q=Motorama&kind=artist&limit=5`

Acceptance per query:

- first request is `cache.status == "miss"`
- second request is `cache.status == "fresh"`
- top result `kind == "artist"`
- top result `canonical_id != null`
- top result `features_json.search_rank_version == "artist_query_v1"`
- cold and warm responses keep the same top `canonical_id`
- cold and warm responses keep the same top youtube and yandex `provider_id`

### Milestone 4: Conditional Search-Only Defect Fix

Enter only if live `/search` is reachable but fails acceptance for a search-local reason.

Allowed edits:

- `app/services/search_service.py`
- `tests/api/test_search.py`
- milestone 6 artifacts

Required checks if a fix is needed:

```bash
.venv/bin/python -m pytest -q tests/api/test_search.py
.venv/bin/ruff check app/services/search_service.py tests/api/test_search.py
```

Re-run live verification on a fresh temp SQLite DB after the fix.

If the failure depends on provider clients, Yandex, worker, detail/frontend code, Redis/runtime availability, or anything outside the allowed edit set, record a blocker instead of widening scope.

## Test Cases And Scenarios

- `Krovostok`: cold miss and warm fresh return the same top canonical artist with `artist_query_v1`
- `Motorama`: cold miss and warm fresh return the same top canonical artist with `artist_query_v1`
- no worker started
- no sync, detail, or frontend route usage
- no unrelated file changes
- any search-only fix must add a targeted regression matching the observed live failure

## Assumptions And Defaults

- this milestone is `Milestone 6`
- isolated API runtime is preferred over a reused runtime when cold and warm proof would be ambiguous
- temp SQLite is the default live verification DB target
- token values, cookies, and auth headers must never be logged
- historical milestone artifacts remain append-only

## Execution Note

- Artifact bootstrap completed as planned.
- Read-only preflight confirmed there was no running local API and no seeded `search:v2` rows for the target queries.
- Repo-local Redis could be started and answered `PONG` via `docker compose exec`, but host-run access to `127.0.0.1:6379` remained unavailable in this environment.
- Because `GET /search` depends on Redis-backed rate limiting and the approved plan explicitly stops on blocked or unreachable `6379`, the milestone ended as a runtime blocker without widening scope into worker, provider, Yandex, or frontend changes.
