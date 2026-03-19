# NETvRF

NETvRF is a FastAPI MVP for cross-platform music search, canonical entity detail pages, and queued sync jobs across YouTube Music and Yandex Music.

As of `2026-03-19`, the verified demo baseline includes mounted API and web UI routes, local SQLite WAL development, a staging-like host-run setup against Dockerized PostgreSQL and Redis, and a separately verified production-like artist sync path with real provider tokens. Broader live provider behavior is still only partially verified and must not be presented as a blanket completed capability.

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
  - `/search` keeps the documented degraded path when the effective provider registry is empty; current default wiring may still return `200` through public Yandex search on a cold miss
- Verified search-first clean-demo behavior on `2026-03-19` with real provider tokens:
  - `./scripts/reset_demo_env.sh` and `./scripts/run_demo_api.sh` produced a clean `8001` demo environment
  - parallel cold-start `Motorama` `/search` and `/ui` both returned `200` after the provider-row race fix
  - `Motorama` and `Krovostok` both stayed stable on cold and warm `/search` and `/ui`
- Separately verified production-like artist sync behavior with real provider tokens on `2026-03-19`:
  - `/jobs/{job_id}` reached `finished`
  - both providers returned `status="updated"`
  - YouTube used `mode="entity_refresh"`
  - Yandex used `mode="catalog_ingest"`
  - `partial=false`
  - post-sync `/artists/{id}` kept non-empty `yandex_catalog_sections`
  - post-sync `/ui/artists/{id}` still showed `Yandex native catalog`
- Not verified for demo claims:
  - live provider search quality with real tokens across arbitrary queries
  - broader live provider behavior beyond the documented `2026-03-19` artist sync snapshot

## First-User MVP Scope

- Certified query set: `Motorama`, `Krovostok`
- Certified flow: `GET /health` -> `/ui` -> artist search on the two certified queries
- Chosen first-tester access path: operator-run demo API on a trusted LAN/VPN
  - operator shares `http://<operator_lan_ip>:8001/ui`
  - no public internet exposure, TLS, or auth layer is part of this MVP milestone
- Recommended clean-demo commands:

```bash
./scripts/reset_demo_env.sh
./scripts/run_demo_api.sh
```

- First-user MVP excludes:
  - `/sync`
  - `/jobs`
  - worker-backed refresh claims
  - broad live-provider quality claims
- Presentation note for `Krovostok`:
  - the current primary CTA label renders `Krovostok - Topic`, so present it as an ambiguity-aware artist overview path, not as a blanket proof of perfect top-label quality

## Demo Runbook

### Private-Network First-Tester Runbook

Use this runbook only for trusted testers on the same LAN or VPN as the operator.

1. Reset the isolated demo environment:

```bash
./scripts/reset_demo_env.sh
```

2. Discover the operator LAN IP on macOS:

```bash
OPERATOR_LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)"
echo "$OPERATOR_LAN_IP"
```

If both commands return nothing, use the machine's current LAN/VPN IP from system settings.

3. Start the demo API in shared mode:

```bash
DEMO_APP_HOST=0.0.0.0 DEMO_ACCESS_HOST="$OPERATOR_LAN_IP" ./scripts/run_demo_api.sh
```

4. Verify locally on the operator machine:

```bash
curl -i http://127.0.0.1:8001/health
curl -i 'http://127.0.0.1:8001/ui?q=Motorama&kind=artist&limit=5'
curl -i 'http://127.0.0.1:8001/ui?q=Krovostok&kind=artist&limit=5'
```

5. Send testers exactly one URL:

```text
http://<operator_lan_ip>:8001/ui
```

6. Ask testers to run only `Motorama` and `Krovostok`.
7. Treat success as:
  - `/ui` opens for the tester
  - both certified queries render
  - the old duplicate-row `500` does not recur
8. If the path fails, stop and fall back to operator-only demo. Do not improvise a public deploy in this milestone.

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

- Broader live provider behavior with real `YOUTUBE_MUSIC_TOKEN` and `YANDEX_MUSIC_TOKEN` is not part of the general verified demo baseline beyond the documented `2026-03-19` artist sync snapshot.
- Provider detail refresh paths (`get_artist`, `get_release`, `get_track`) are implemented and were exercised in the `2026-03-19` production-like artist sync snapshot, but broader live-provider coverage remains partial.
- Successful detail, sync, and job success-path demos depend on pre-existing canonical rows or known IDs in the active database.
- Search cache refresh remains out of scope, and worker-based sync execution has one documented green production-like artist sync result rather than a blanket readiness claim.
- `Krovostok` is certified as a stable query, but its current primary CTA label is `Krovostok - Topic`; keep user-testing claims query-specific and ambiguity-aware.
- The first-tester access path is private-network only. This repository still does not provide a public deployment target, TLS termination, or application-layer auth for open internet exposure.

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
