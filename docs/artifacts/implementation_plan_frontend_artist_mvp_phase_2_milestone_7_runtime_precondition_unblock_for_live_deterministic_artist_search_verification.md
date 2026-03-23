# Implementation Plan: Frontend Artist MVP Phase 2 Milestone 7 Runtime Precondition Unblock For Live Deterministic Artist Search Verification

Status: executed and blocked on `2026-03-19`.

## Summary

- Goal: unblock a trustworthy API-only runtime path for live deterministic artist search verification without starting worker and without changing application code.
- Scope: local runtime verification path and milestone 7 artifacts only.
- Historical note: milestone 6 remains blocked on `2026-03-19`; milestone 7 is the newer dated successor for the runtime-precondition unblock attempt.
- Out of scope:
  - `app/*`, `tests/*`, `.env*`, `docker-compose*.yml`
  - search ranking logic, Yandex subsystem, worker, sync, frontend runtime, artist detail pages
  - unrelated dirty files and historical milestone artifacts

## Source Of Truth

- `docs/project_brief.md`
- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_6_live_runtime_verification_for_deterministic_artist_search.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_6_live_runtime_verification_for_deterministic_artist_search.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`

## Grounded Facts

- This sandbox denies host localhost TCP connections with `PermissionError`, including `127.0.0.1:6379`, `:6380`, `:5432`, `:5433`, `:8000`, and `:8001`.
- This sandbox also denies host Unix domain socket bind/connect operations:
  - direct host connect to the bind-mounted Redis socket returned `PermissionError`
  - a control probe that tried to bind a host-created Unix socket in `/tmp` also returned `PermissionError`
- `redis-py` in the project venv accepts Unix socket URLs like `unix:///tmp/.../redis.sock?db=0`.
- `uvicorn` in the project venv supports `--uds`.
- `curl` in this environment supports `--unix-socket`.
- `/search` still depends on Redis-backed rate limiting, so live verification must prove reachable Redis from the API runtime.
- Worker must remain stopped for this milestone.

## Public Interface Impact

- No API schema, route, or type changes.
- No repo-tracked runtime config changes.
- Milestone-only runtime transport override:
  - Redis URL: `unix:///tmp/.../redis.sock?db=0`
  - API socket: `/tmp/.../api.sock`

## Runtime Topology

Create one unique temp runtime directory per run:

```bash
export M7_RUNTIME_DIR="$(mktemp -d /tmp/netvrf-m7-runtime.XXXXXX)"
export M7_DB_URL="sqlite+pysqlite:///$M7_RUNTIME_DIR/netvrf.db"
export M7_REDIS_URL="unix://$M7_RUNTIME_DIR/redis.sock?db=0"
export M7_API_SOCK="$M7_RUNTIME_DIR/api.sock"
export M7_COMPOSE_PROJECT="netvrf-m7-uds"
export M7_OVERRIDE_FILE="$M7_RUNTIME_DIR/redis-uds.override.yml"
chmod 0777 "$M7_RUNTIME_DIR"
```

Create a temp override file outside the repo:

```yaml
services:
  redis:
    ports: !override []
    volumes:
      - redis_data:/data
      - __RUNTIME_DIR__:/run/netvrf
    command:
      - redis-server
      - --appendonly
      - yes
      - --port
      - "0"
      - --unixsocket
      - /run/netvrf/redis.sock
      - --unixsocketperm
      - "777"
    healthcheck:
      test: ["CMD", "redis-cli", "-s", "/run/netvrf/redis.sock", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
```

## Execution Slices

### Slice 0: Artifact Bootstrap

1. Create this milestone 7 Implementation Plan artifact first.
2. Create the milestone 7 Walkthrough artifact second.
3. Record dirty worktree with `git status --short`.
4. Keep milestone 6 append-only and untouched.

### Slice 1: Redis UDS Unblock

Run only:

```bash
git status --short
.venv/bin/python - <<'PY'
from dotenv import dotenv_values
values = dotenv_values(".env")
print("youtube_token=present" if values.get("YOUTUBE_MUSIC_TOKEN") else "youtube_token=missing")
print("yandex_token=present" if values.get("YANDEX_MUSIC_TOKEN") else "yandex_token=missing")
PY
docker compose -p "$M7_COMPOSE_PROJECT" -f docker-compose.yml -f "$M7_OVERRIDE_FILE" down -v
docker compose -p "$M7_COMPOSE_PROJECT" -f docker-compose.yml -f "$M7_OVERRIDE_FILE" up -d redis
docker compose -p "$M7_COMPOSE_PROJECT" -f docker-compose.yml -f "$M7_OVERRIDE_FILE" exec -T redis redis-cli -s /run/netvrf/redis.sock ping
.venv/bin/python - <<'PY'
import os
from redis import Redis
url = os.environ["M7_REDIS_URL"]
client = Redis.from_url(url, decode_responses=True)
print(f"host_redis_ping={client.ping()}")
PY
```

Acceptance:

- token presence probe reports both tokens as `present` without printing values
- container Redis ping returns `PONG`
- host Redis ping over the Unix socket returns `True`

If this slice fails, stop and document the exact blocker without widening scope.

### Slice 2: API-Only Startup On UDS

Use only temp SQLite and no worker:

```bash
env DATABASE_URL="$M7_DB_URL" .venv/bin/alembic upgrade head
/bin/zsh -lc '.venv/bin/python - <<'"'"'PY'"'"'
import os
from dotenv import dotenv_values

env = os.environ.copy()
values = dotenv_values(".env")
for key in ("YOUTUBE_MUSIC_TOKEN", "YANDEX_MUSIC_TOKEN"):
    value = values.get(key)
    if value:
        env[key] = value

env.update({
    "APP_DEBUG": "false",
    "APP_RELOAD": "false",
    "HEALTH_REQUIRE_REDIS": "true",
    "DATABASE_URL": os.environ["M7_DB_URL"],
    "REDIS_URL": os.environ["M7_REDIS_URL"],
    "PROVIDER_HTTP_TIMEOUT_SECONDS": "15",
    "SEARCH_PROVIDER_TIMEOUT_SECONDS": "15",
    "PYTHONUNBUFFERED": "1",
})
os.execvpe(
    ".venv/bin/python",
    [".venv/bin/python", "-m", "uvicorn", "app.main:create_app", "--factory", "--uds", os.environ["M7_API_SOCK"]],
    env,
)
PY'
curl --unix-socket "$M7_API_SOCK" -sS -i http://localhost/health
```

Acceptance:

- API starts in one long-lived session with `uvicorn --uds`
- worker is not started
- `/health` returns HTTP `200`
- payload reports `status="ok"`, `database.status="ok"`, and `redis.status="ok"`

If this slice fails, stop and document the exact blocker.

### Slice 3: Live Deterministic Artist Search Verification

Probe only:

- `/search?q=Krovostok&kind=artist&limit=5`
- `/search?q=Motorama&kind=artist&limit=5`

Run each query twice through the API Unix socket and print only:

- `query`
- `request_index`
- `status_code`
- `cache.status`
- `partial`
- `missing_platforms`
- `top.kind`
- `top.canonical_id`
- `top.youtube.provider_id`
- `top.yandex.provider_id`
- `top.features_json.search_rank_version`

Acceptance per query:

- first response is HTTP `200` with `cache.status == "miss"`
- second response is HTTP `200` with `cache.status == "fresh"`
- `partial is false`
- `missing_platforms == []`
- top result exists and `kind == "artist"`
- top `canonical_id` is not `null`
- top YouTube and Yandex `provider_id` values are present
- top `features_json.search_rank_version == "artist_query_v1"`
- cold and warm responses keep the same top `canonical_id`
- cold and warm responses keep the same top YouTube `provider_id`
- cold and warm responses keep the same top Yandex `provider_id`

If the runtime path is green but live search fails because of egress, provider timeout, partial response, or unstable top result, document that exact blocker and keep search code untouched.

### Slice 4: Closeout

1. Stop only the isolated Redis compose project.
2. Record the temp runtime dir path in the Walkthrough.
3. Explicitly state that worker was not started.
4. Keep repo-tracked diff limited to the milestone 7 artifacts.

## Test Cases And Scenarios

- Redis reachable from container over UDS
- Redis reachable from host runtime over UDS
- temp SQLite DB migrates successfully
- `/health` returns `200` with healthy DB and Redis
- `Krovostok` cold and warm results keep the same top canonical artist and provider IDs
- `Motorama` cold and warm results keep the same top canonical artist and provider IDs
- worker is never started
- if any step fails, blocker is captured exactly with no scope widening and no search-code edits

## Assumptions And Defaults

- this milestone is `Milestone 7`
- milestone 6 remains historical and blocked on `2026-03-19`
- Unix sockets are the approved transport for this milestone because localhost TCP is blocked in this sandbox
- temp SQLite is the default verification database
- only Redis is started under Docker Compose
- provider tokens are loaded from `.env` via `python-dotenv`; values are never printed
- if provider HTTP egress fails after `/health` is green, that is a runtime blocker to document, not a reason to change code

## Execution Note

- Slice 0 completed:
  - created the milestone 7 Implementation Plan artifact first
  - created the milestone 7 Walkthrough artifact second
- Slice 1 reached a new runtime blocker:
  - token presence probe reported both provider tokens as present without printing values
  - isolated Redis started successfully under Docker Compose
  - container-side Redis ping over `/run/netvrf/redis.sock` returned `PONG`
  - the bind-mounted `redis.sock` file appeared on the host in the temp runtime directory
  - host-side `redis-py` ping over `unix:///tmp/.../redis.sock?db=0` failed
  - direct host `AF_UNIX` connect to the same socket returned `PermissionError`
  - a host-only control probe could not even `bind()` a fresh Unix socket under `/tmp`
- Conclusion:
  - the planned UDS workaround is blocked by sandbox socket permissions before API startup
  - Slice 2 `/health` and Slice 3 live `/search` verification were not run
  - worker was not started
  - search code, runtime code, and historical milestone artifacts remained untouched

## Newer State — 2026-03-19T05:14:55+03:00

Status: blocked on `2026-03-19`; this entry is append-only newer state for milestone 7.

### Historical Continuity

- milestone 6 remained blocked on `2026-03-19` at runtime preconditions, not at search logic
- this milestone 7 entry is the newer dated state and must remain append-only

### Scope Lock

- local runtime verification path only
- milestone 7 artifacts only
- no edits to `app/*`, `tests/*`, `.env*`, `docker-compose*.yml`, search ranking code, Yandex subsystem, worker, sync, frontend runtime, artist detail pages, or unrelated dirty files

### Execution Strategy

1. Append a new milestone 7 state block to the Implementation Plan artifact first.
2. Append a new milestone 7 state block to the Walkthrough artifact second.
3. Re-run safe capability preflight:
   - `git status --short`
   - safe token-presence probe
   - host localhost TCP probe for Redis and API ports
   - host Unix socket bind probe
   - `docker ps` inventory
4. Transport selection is fixed by probe outputs:
   - use host TCP only if localhost is reachable
   - use Unix sockets only if host AF_UNIX operations are permitted
   - if both remain blocked with `PermissionError`, stop before isolated runtime bring-up
5. If Slice 1 is green, continue with isolated temp runtime resources only:
   - temp SQLite WAL DB under `/tmp`
   - isolated Redis only
   - API-only startup with `HEALTH_REQUIRE_REDIS=true`
   - `/health` probe, then cold/warm `/search` verification for `Krovostok` and `Motorama`
6. If any slice blocks, document the exact blocker and keep worker stopped.

### Expected Diff

- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_7_runtime_precondition_unblock_for_live_deterministic_artist_search_verification.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_7_runtime_precondition_unblock_for_live_deterministic_artist_search_verification.md`

### Execution Result For This Newer State

- Slice 0 completed:
  - appended this newer dated milestone 7 state to the Implementation Plan artifact first
  - appended the matching newer dated state to the Walkthrough artifact second
- Slice 1 capability preflight completed and hit the fixed stop condition:
  - safe token-presence probe stayed green without printing token values
  - host localhost TCP connect attempts to `127.0.0.1:6379`, `:8000`, and `:8001` failed with `PermissionError`
  - host AF_UNIX bind under `/tmp` failed with `PermissionError`
  - `docker ps` confirmed container presence only; it did not change the blocked host transport facts
- Decision:
  - no transport option from the plan remained viable
  - isolated runtime bring-up, `alembic upgrade head`, `/health`, and live `/search` verification were not attempted
- Conclusion:
  - milestone 7 newer state is blocked at runtime transport preconditions, outside the allowed milestone scope
  - worker was not started
  - search code, app runtime code, tests, and historical artifacts remained untouched

## Newer State — 2026-03-19T05:29:52+03:00

Status: executed and blocked on `2026-03-19` at Slice 1 runtime transport preconditions.

### Historical Continuity

- milestone 6 remained blocked on `2026-03-19` at runtime preconditions, not at search logic
- this milestone 7 section is a newer dated append-only state

### Scope Lock

- local runtime verification path only
- milestone 7 artifacts only
- no edits to `app/*`, `tests/*`, `.env*`, `docker-compose*.yml`, search ranking code, Yandex subsystem, worker, sync, frontend runtime, artist detail pages, or unrelated dirty files

### Probe-Driven Execution Slices

1. Slice 0: append this newer milestone 7 state to the Implementation Plan artifact first, then append the matching newer state to the Walkthrough artifact second.
2. Slice 1: re-run only safe capability preflight:
   - `git status --short`
   - safe token-presence probe from `.env`
   - host localhost TCP probe for `127.0.0.1:6379`, `:8000`, and `:8001`
   - host Unix socket bind probe under `/tmp`
   - `docker ps --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'`
3. Transport selection stays fixed by Slice 1 outputs:
   - `TCP Redis + TCP API` only if host TCP is usable
   - `TCP Redis + API UDS` only if host TCP is usable and host AF_UNIX is usable
   - `Redis UDS + API UDS` only if host AF_UNIX is usable
   - stop immediately if both host TCP and host AF_UNIX are blocked
4. Run Slice 2 through Slice 5 only if Slice 1 proves a reachable host transport.

### Execution Result For This Newer State

- Slice 0 completed:
  - new milestone 7 state appended to the Implementation Plan artifact first
  - matching milestone 7 state appended to the Walkthrough artifact second
- Slice 1 completed and hit the fixed stop condition:
  - safe token-presence probe stayed green without printing values
  - host localhost TCP connect attempts to `127.0.0.1:6379`, `:8000`, and `:8001` all failed with `PermissionError`
  - host AF_UNIX bind under `/tmp` failed with `PermissionError`
  - `docker ps` showed container inventory only and did not change the blocked host transport facts
- Transport outcome:
  - `TCP Redis + TCP API` rejected because host TCP remained blocked
  - `TCP Redis + API UDS` rejected because host AF_UNIX remained blocked
  - `Redis UDS + API UDS` rejected because host AF_UNIX remained blocked
- Consequence:
  - isolated runtime bring-up, `alembic upgrade head`, `/health`, and live `/search` verification were not attempted in this newer state

### Conclusion

- milestone 7 newer state is blocked at Slice 1 runtime transport preconditions, outside the allowed milestone scope
- this blocker is environmental rather than a search-local defect
- worker was not started
- search code, app runtime code, tests, and historical artifacts remained untouched

## Newer State — 2026-03-19T05:58:27+03:00

Status: executed and verified on `2026-03-19` via a user-run local runtime path outside the blocked sandbox transport boundary.

### Historical Continuity

- milestone 6 remained blocked on `2026-03-19` at runtime preconditions, not at search logic
- earlier milestone 7 states captured sandbox transport blockers with host TCP and host AF_UNIX denied
- this milestone 7 section is a newer dated append-only state that records the successful local runtime verification path

### Scope Lock

- local runtime verification path only
- milestone 7 artifacts only
- no edits to `app/*`, `tests/*`, `.env*`, `docker-compose*.yml`, search ranking code, Yandex subsystem, worker, sync, frontend runtime, artist detail pages, or unrelated dirty files

### Verified Runtime Path

- transport: `TCP Redis + TCP API`
- isolated Redis:
  - container name: `netvrf-m7-redis`
  - runtime Redis URL: `redis://127.0.0.1:6381/0`
- API-only runtime:
  - host: `127.0.0.1`
  - port: `8001`
  - database: `sqlite+pysqlite:////tmp/netvrf-m7-runtime/netvrf.db`
  - exact process command confirmed from the live listener:
    - `/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8001`
- worker remained stopped

### Execution Result For This Newer State

- Slice 0 artifact continuity preserved:
  - this newer state was appended to the Implementation Plan artifact first
  - the matching execution log was appended to the Walkthrough artifact second
- Slice 1 runtime preconditions were satisfied in the user-run local shell:
  - Redis container `netvrf-m7-redis` was running
  - listener on `127.0.0.1:8001` was confirmed
  - a stray listener on `127.0.0.1:8000` was identified and stopped
- Slice 2 runtime bring-up evidence was green:
  - `docker exec netvrf-m7-redis redis-cli ping` returned `PONG`
- Slice 3 API-only startup evidence was green:
  - `GET /health` returned HTTP `200`
  - payload reported `status="ok"`, `database.status="ok"`, and `redis.status="ok"`
- Slice 4 live deterministic artist search verification was green:
  - `Krovostok`
    - request 1: `cache.status="miss"`
    - request 2: `cache.status="fresh"`
    - both requests: `partial=false`, `missing_platforms=[]`
    - both requests: top result `kind="artist"`, `canonical_id=1`
    - both requests: top youtube `provider_id="UCi-dSgoZzJRuV5AWDkQi9zA"`
    - both requests: top yandex `provider_id="218095"`
    - both requests: `top.features_json.search_rank_version="artist_query_v1"`
  - `Motorama`
    - request 1: `cache.status="miss"`
    - request 2: `cache.status="fresh"`
    - both requests: `partial=false`, `missing_platforms=[]`
    - both requests: top result `kind="artist"`, `canonical_id=2`
    - both requests: top youtube `provider_id="UC9Vtn5WRFoHdkb5fbXswmWw"`
    - both requests: top yandex `provider_id="1014281"`
    - both requests: `top.features_json.search_rank_version="artist_query_v1"`

### Conclusion

- milestone 7 runtime precondition unblock is verified green on the user-run local runtime path
- the milestone acceptance target is satisfied:
  - reachable API-only runtime path with reachable Redis
  - `/health` returned `200` with healthy DB and Redis
  - worker was not started
  - live deterministic artist search verification completed for `Krovostok` and `Motorama`
- no application code changes were required to unblock this milestone
