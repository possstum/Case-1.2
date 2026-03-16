# Runtime Verification: Verified Local And Staging-Like MVP Baseline

Этот artifact фиксирует verified baseline, на который опираются `README.md`, `docs/project_brief.md`, и demo runbook по состоянию на `2026-03-16`.

Ключевая граница:

- verified local baseline включает точные команды, route probe, temp-SQLite smoke, rate-limit checks и redaction smoke
- verified staging-like baseline включает host-run app against PostgreSQL + Redis с blank provider tokens
- live provider behavior with real tokens remains unverified and intentionally excluded from demo claims
- в этом CI alignment pass runtime claims не расширялись; был только повторно подтвержден minimal lint/pytest baseline и выровнен narrative

## 1. Verified Local Baseline

### Commands Actually Run

```bash
.venv/bin/python -m pip install -e '.[dev]'
```

```bash
.venv/bin/ruff check .
```

```bash
.venv/bin/pytest -q tests/api
```

```bash
.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core
```

```bash
.venv/bin/python - <<'PY'
from app.main import create_app

app = create_app()
routes = sorted(
    (sorted(route.methods), route.path)
    for route in app.routes
    if getattr(route, "path", None) in {
        "/health",
        "/search",
        "/artists/{artist_id}",
        "/releases/{release_id}",
        "/tracks/{track_id}",
        "/sync/{kind}/{target_id}",
        "/jobs/{job_id}",
    }
)
for methods, path in routes:
    print(",".join(methods), path)
PY
```

```bash
.venv/bin/python - <<'PY'
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config

ROOT = Path.cwd()

tmpdir = Path(tempfile.mkdtemp(prefix="netvrf-runtime-smoke-"))
db_path = tmpdir / "runtime.db"
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"

from tests.conftest import reset_runtime_caches

reset_runtime_caches()

config = Config(str(ROOT / "alembic.ini"))
config.set_main_option("script_location", str(ROOT / "alembic"))
command.upgrade(config, "head")

from app.db.session import get_session_factory
from app.providers import ProviderRegistry
from tests.api.test_search import (
    AllowAllLimiter as SearchAllowAllLimiter,
    DenyAllLimiter as SearchDenyAllLimiter,
    RecordingScheduler,
    create_search_client,
)
from tests.test_support import (
    AllowAllLimiter,
    DenyAllLimiter,
    create_test_client,
    seed_catalog,
)

session = get_session_factory()()
try:
    ids = seed_catalog(session)
finally:
    session.close()

with create_test_client(limiter=AllowAllLimiter()) as client:
    for path in ("/artists/99999", "/releases/99999", "/tracks/99999"):
        response = client.get(path)
        print(path, response.status_code, response.json()["error"]["code"])

with create_search_client(
    provider_registry=ProviderRegistry(()),
    refresh_scheduler=RecordingScheduler(),
    limiter=SearchAllowAllLimiter(),
) as client:
    response = client.get("/search", params={"q": "Motorama", "kind": "artist", "limit": 5})
    print("search_no_providers", response.status_code, response.json()["error"]["code"])

with create_search_client(
    provider_registry=ProviderRegistry(()),
    refresh_scheduler=RecordingScheduler(),
    limiter=SearchDenyAllLimiter(),
) as client:
    headers = {"X-Correlation-ID": "cid-search-runtime"}
    response = client.get("/search", params={"q": "Motorama", "kind": "artist", "limit": 5}, headers=headers)
    print(
        "search_rate_limit",
        response.status_code,
        response.json()["error"]["code"],
        response.headers["X-Correlation-ID"],
        response.json()["error"]["correlation_id"],
    )

with create_test_client(limiter=DenyAllLimiter()) as client:
    headers = {"X-Correlation-ID": "cid-sync-runtime"}
    response = client.post(f"/sync/artist/{ids['artist_id']}", headers=headers)
    print(
        "sync_rate_limit",
        response.status_code,
        response.json()["error"]["code"],
        response.headers["X-Correlation-ID"],
        response.json()["error"]["correlation_id"],
    )

reset_runtime_caches()
PY
```

```bash
.venv/bin/python - <<'PY'
from __future__ import annotations

import logging
from io import StringIO

from app.core.logging import CorrelationIdFilter, JsonFormatter, RedactionFilter
from app.core.middleware import correlation_id_ctx

buffer = StringIO()
handler = logging.StreamHandler(buffer)
handler.setFormatter(JsonFormatter())
handler.addFilter(RedactionFilter())
handler.addFilter(CorrelationIdFilter())

root = logging.getLogger()
root.handlers.clear()
root.setLevel("INFO")
root.addHandler(handler)

correlation_token = correlation_id_ctx.set("cid-redaction-runtime")
try:
    logging.getLogger("runtime.smoke").info(
        "provider_request headers=%s",
        {
            "Authorization": "Bearer fake-token-123",
            "Cookie": "sessionid=fake-cookie-456; path=/",
            "nested": [{"token": "nested-fake-token-789"}],
        },
    )
finally:
    correlation_id_ctx.reset(correlation_token)

output = buffer.getvalue().strip()
print(output)
print("redaction_smoke", "***REDACTED***" in output, "fake-token-123" in output, "fake-cookie-456" in output, "nested-fake-token-789" in output)
PY
```

### Exact Local Results

| Command | Exact result |
| --- | --- |
| `.venv/bin/python -m pip install -e '.[dev]'` | completed successfully; editable `netvrf` install refreshed and `ruff` installed |
| `.venv/bin/ruff check .` | `All checks passed!` |
| `.venv/bin/pytest -q tests/api` | `24 passed in 1.65s` |
| `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core` | `28 passed in 0.55s` |

### Exact Local Route Probe Output

```text
GET /artists/{artist_id}
GET /health
GET /jobs/{job_id}
GET /releases/{release_id}
GET /search
GET /tracks/{track_id}
POST /sync/{kind}/{target_id}
```

### Exact Temp-SQLite Smoke Output

Note: the probe also emitted Alembic INFO lines while creating the isolated SQLite baseline. The behavior-relevant output was:

```text
/artists/99999 404 not_found
/releases/99999 404 not_found
/tracks/99999 404 not_found
search_no_providers 503 search_providers_unavailable
search_rate_limit 429 rate_limit_exceeded cid-search-runtime cid-search-runtime
sync_rate_limit 429 rate_limit_exceeded cid-sync-runtime cid-sync-runtime
```

### Exact Redaction Smoke Summary

- emitted JSON log line contained `***REDACTED***` instead of raw `Authorization`, `Cookie`, and nested `token` values
- final summary line was:

```text
redaction_smoke True False False False
```

## 2. Verified Staging-Like Baseline

Этот раздел фиксирует уже подтвержденный host-run app flow against Dockerized PostgreSQL and Redis. Он intentionally exercises degraded provider mode with blank provider tokens from `.env.staging.example`.

### Verified Command Set

Terminal 1:

```bash
.venv/bin/python -m pip install -e '.[dev]'
cp .env.staging.example .env.staging
docker compose up -d postgres redis
until docker compose exec postgres pg_isready -U netvrf -d netvrf >/dev/null 2>&1; do sleep 1; done
until docker compose exec redis redis-cli ping >/dev/null 2>&1; do sleep 1; done
set -a
. ./.env.staging
set +a
.venv/bin/alembic upgrade head
./scripts/run_api.sh
```

Terminal 2:

```bash
curl -i http://127.0.0.1:8000/health
curl -i 'http://127.0.0.1:8000/search?q=Motorama&kind=artist&limit=5'
docker compose exec postgres psql -U netvrf -d netvrf -c "select version_num from alembic_version;"
docker compose exec postgres psql -U netvrf -d netvrf -c "select tablename from pg_tables where schemaname='public' and tablename in ('artists','search_cache','sync_jobs') order by tablename;"
docker compose down
```

### Exact Staging-Like Results

- `GET /health` returned `200` with `status=ok`, `database.status=ok`, and `redis.status=ok`
- `GET /search` returned `503` with `error.code=search_providers_unavailable`
- `alembic_version.version_num` equaled `7f6b4e2c9a11`
- the table check included `artists`, `search_cache`, and `sync_jobs`

### What This Staging-Like Run Verifies

- host-run app against PostgreSQL + Redis works
- degraded provider mode with blank tokens is expected and documented
- DB schema and health checks are sufficient for the MVP demo baseline

### What This Staging-Like Run Does Not Verify

- live provider search results with real tokens
- live provider detail refresh via sync worker
- end-to-end successful provider refresh through `run_sync_job`

## 3. Demo-Facing Expectation Matrix

| Route | Accepted baseline behavior |
| --- | --- |
| `GET /health` | `200`; in staging-like baseline database and Redis should both be `ok` |
| `GET /search` | `200` from fresh/stale cache, or `503 search_providers_unavailable` for cold miss / expired cache with blank tokens |
| `GET /artists/{id}` | `200` when the ID exists, otherwise acceptable `404 not_found` |
| `GET /releases/{id}` | `200` when the ID exists, otherwise acceptable `404 not_found` |
| `GET /tracks/{id}` | `200` when the ID exists, otherwise acceptable `404 not_found` |
| `POST /sync/{kind}/{id}` | `202` when target exists and queueing works, otherwise acceptable `404 not_found` on a fresh DB |
| `GET /jobs/{job_id}` | `200` for an existing job, acceptable `404 not_found` for an unknown ID |
| `GET /ui` | `200`; provider-disabled notice is acceptable when providers are unavailable |

## 4. Verified Behavior Matrix

| Verified fact | Evidence | Observed result | Verification status |
| --- | --- | --- | --- |
| canonical local install command works | `.venv/bin/python -m pip install -e '.[dev]'` | editable install completed successfully | verified |
| canonical local lint command is green | `.venv/bin/ruff check .` | `All checks passed!` | verified |
| verified API pytest baseline matches CI step 1 | `.venv/bin/pytest -q tests/api` | `24 passed in 1.65s` | verified |
| verified non-api pytest baseline matches CI step 2 | `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core` | `28 passed in 0.55s` | verified |
| `/health` is mounted | route probe via `create_app().routes` | `GET /health` present | verified |
| `/search` is mounted | route probe via `create_app().routes` | `GET /search` present | verified |
| `/artists/{id}` detail route is mounted | route probe via `create_app().routes` | `GET /artists/{artist_id}` present | verified |
| `/releases/{id}` detail route is mounted | route probe via `create_app().routes` | `GET /releases/{release_id}` present | verified |
| `/tracks/{id}` detail route is mounted | route probe via `create_app().routes` | `GET /tracks/{track_id}` present | verified |
| `/sync/{kind}/{id}` sync route family is mounted | route probe via `create_app().routes` | exact runtime path is `POST /sync/{kind}/{target_id}` | verified |
| `/jobs/{job_id}` is mounted | route probe via `create_app().routes` | `GET /jobs/{job_id}` present | verified |
| missing entity IDs return domain-level `404` | temp-SQLite smoke probe through `TestClient` | artist, release, and track requests returned `404` with `error.code="not_found"` | verified |
| search without configured providers returns `503 search_providers_unavailable` on cold miss | temp-SQLite smoke probe with `ProviderRegistry(())` | tested cold-miss path returned `503 search_providers_unavailable` | verified for the tested cold-miss path |
| `/search` rate limiting was manually observed with `429` | temp-SQLite smoke probe using `DenyAllLimiter()` | `429 rate_limit_exceeded` | verified |
| `/sync` rate limiting was manually observed with `429` | temp-SQLite smoke probe using `DenyAllLimiter()` | `429 rate_limit_exceeded` | verified |
| `X-Correlation-ID` was manually confirmed on search responses | temp-SQLite smoke probe with `X-Correlation-ID: cid-search-runtime` | response header and `error.correlation_id` both echoed `cid-search-runtime` | verified |
| redaction smoke-check passed | log pipeline smoke probe using `RedactionFilter`, `CorrelationIdFilter`, and `JsonFormatter` | `***REDACTED***` present; fake token values absent | verified |
| staging-like `/health` works against PostgreSQL + Redis | staging-like host-run verification | `200` with both dependencies `ok` | verified |
| staging-like `/search` degraded mode is documented and reproducible | staging-like host-run verification | `503 search_providers_unavailable` with blank tokens | verified |

## 5. Unverified Live-Provider Behavior

The following items must remain outside demo claims until they are separately re-verified:

- search quality and stability with real provider tokens
- provider detail refresh methods used by sync execution
- successful end-to-end live provider refresh through worker execution
- any claim that `queued` implies eventual successful provider update
