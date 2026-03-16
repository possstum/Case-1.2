# NETvRF

NETvRF is a FastAPI MVP for cross-platform music search, canonical entity detail pages, and queued sync jobs across YouTube Music and Yandex Music.

As of `2026-03-16`, the verified demo baseline includes mounted API and web UI routes, local SQLite WAL development, and a staging-like host-run setup against Dockerized PostgreSQL and Redis. Live provider behavior with real tokens is still not verified and must not be presented as a completed capability.

## Stack

- FastAPI
- Pydantic Settings
- SQLAlchemy 2.x + Alembic
- Redis + RQ
- SQLite WAL for local development
- PostgreSQL + Redis via Docker Compose for staging-like verification

## Verified MVP Baseline

- Mounted API routes: `/health`, `/search`, `/artists/{id}`, `/releases/{id}`, `/tracks/{id}`, `/sync/{kind}/{id}`, `/jobs/{job_id}`
- Mounted web UI routes: `/`, `/ui`, `/ui/*`
- Verified local behavior:
  - `/health` returns `200`
  - `/search` rate limiting returns `429`
  - `/sync` rate limiting returns `429`
  - missing entity IDs return `404 not_found`
  - log redaction masks `Authorization`, `Cookie`, and token-like values
- Verified staging-like behavior with blank provider tokens:
  - `/health` returns `200` with database and Redis both `ok`
  - `/search` returns `503 search_providers_unavailable` on cold miss
- Not verified for demo claims:
  - live provider search quality with real tokens
  - provider `get_*()` refresh paths used by sync execution
  - successful end-to-end live provider refresh via worker

## Demo Runbook

### Dev Start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
mkdir -p data
.venv/bin/alembic upgrade head
./scripts/run_api.sh
```

### Staging-Like Start

```bash
python3 -m venv .venv
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

### Routes To Demo

Start with these routes in order:

```bash
curl -i http://127.0.0.1:8000/health
curl -i http://127.0.0.1:8000/ui
curl -i 'http://127.0.0.1:8000/search?q=Motorama&kind=artist&limit=5'
```

Optional follow-up routes only when you already have known canonical IDs or job IDs in the current database:

```bash
curl -i http://127.0.0.1:8000/artists/<artist_id>
curl -i http://127.0.0.1:8000/releases/<release_id>
curl -i http://127.0.0.1:8000/tracks/<track_id>
curl -i -X POST http://127.0.0.1:8000/sync/artist/<artist_id>
curl -i http://127.0.0.1:8000/jobs/<job_id>
```

### Acceptable Degraded Behavior

- `GET /search` may return `503` with `error.code=search_providers_unavailable` when provider tokens are blank and the request is a cold miss or an expired-cache miss.
- `GET /search` may still return `200` from a fresh or stale cache even when providers are not configured.
- `GET /ui` may render a provider-disabled notice instead of live search results.
- `GET /artists/{id}`, `GET /releases/{id}`, and `GET /tracks/{id}` may return `404 not_found` on a fresh database with no canonical rows.
- `POST /sync/{kind}/{id}` may return `404 not_found` on a fresh database; `202` is expected only when the target exists and queueing succeeds.
- `GET /jobs/{job_id}` may return `404 not_found` for an unknown ID, or `200` with `queued`, `finished`, or `failed` for an existing job.
- `queued` or `failed` job states are acceptable in the demo baseline; do not claim successful live provider refresh unless it has been separately verified.

## Final Smoke Checklist

| Route | Expected baseline result |
| --- | --- |
| `GET /health` | `200`; in staging-like mode `status=ok`, `database.status=ok`, `redis.status=ok` |
| `GET /search` | `200` from fresh/stale cache, or `503 search_providers_unavailable` for cold miss / expired cache with blank provider tokens |
| `GET /artists/{id}` | `200` when the ID exists, otherwise acceptable `404 not_found` |
| `GET /releases/{id}` | `200` when the ID exists, otherwise acceptable `404 not_found` |
| `GET /tracks/{id}` | `200` when the ID exists, otherwise acceptable `404 not_found` |
| `POST /sync/{kind}/{id}` | `202` when the target exists and queueing works, otherwise acceptable `404 not_found` on a fresh DB |
| `GET /jobs/{job_id}` | `200` for an existing job with `queued`, `finished`, or `failed`; acceptable `404 not_found` for an unknown ID |
| `GET /ui` | `200`; provider-disabled notice is acceptable when live providers are unavailable |

## Known Limitations

- Live provider behavior with real `YOUTUBE_MUSIC_TOKEN` and `YANDEX_MUSIC_TOKEN` is not part of the verified demo baseline.
- Provider detail refresh paths (`get_artist`, `get_release`, `get_track`) are not verified for demo claims.
- Successful detail, sync, and job success-path demos depend on pre-existing canonical rows or known IDs in the active database.
- Search cache refresh and worker-based sync execution exist in code, but live-provider success claims remain out of scope for this docs pass.

## Backup / Restore Smoke Checklist

### Dev SQLite WAL

Create a safe backup and confirm that it opens:

```bash
sqlite3 data/netvrf.db ".backup '/tmp/netvrf-demo-backup.db'"
sqlite3 /tmp/netvrf-demo-backup.db '.tables'
```

### Staging-Like PostgreSQL

Create a disposable dump, restore it into a disposable database, verify tables, then rerun `/health` against the real app database:

```bash
docker compose exec postgres pg_dump -U netvrf -d netvrf > /tmp/netvrf-demo.sql
docker compose exec postgres psql -U netvrf -d postgres -c 'drop database if exists netvrf_restore_smoke;'
docker compose exec postgres psql -U netvrf -d postgres -c 'create database netvrf_restore_smoke;'
docker compose exec -T postgres psql -U netvrf -d netvrf_restore_smoke < /tmp/netvrf-demo.sql
docker compose exec postgres psql -U netvrf -d netvrf_restore_smoke -c '\dt'
curl -i http://127.0.0.1:8000/health
docker compose exec postgres psql -U netvrf -d postgres -c 'drop database if exists netvrf_restore_smoke;'
```

## Verified Local Vs CI Commands

The minimal GitHub Actions baseline mirrors the verified local commands. The command body stays the same; CI drops the local `.venv/bin/` prefix.

| Step | Local | CI |
| --- | --- | --- |
| install deps | `.venv/bin/python -m pip install -e '.[dev]'` | `python -m pip install -e '.[dev]'` |
| lint | `.venv/bin/ruff check .` | `ruff check .` |
| pytest api | `.venv/bin/pytest -q tests/api` | `pytest -q tests/api` |
| pytest non-api | `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core` | `pytest -q tests/services tests/providers tests/db tests/utils tests/core` |

Current CI intentionally does not include an image build step. The repository has no `Dockerfile`, and `docker-compose.yml` defines infra services only.

Current CI also does not include staging deploy. The repository does not yet contain a deployment workflow, environment approval gate, or staging deployment target that CI could invoke.

## Notes

- All application errors use a single `{"error": ...}` envelope.
- Every request gets an `X-Correlation-ID` header; incoming values are preserved if provided.
- Search and sync endpoints use Redis-backed fixed-window IP rate limits. Defaults are `SEARCH_RATE_LIMIT=30` and `SYNC_RATE_LIMIT=5` over `60` seconds.
- Provider tokens must come from env or deployment secrets. Do not hardcode them; log redaction masks `Authorization`, `Cookie`, and token-like values.
- SQLite development mode enables WAL and foreign keys automatically.
