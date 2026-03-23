# Implementation Plan: Demo Runtime Reset And Bootstrap

Status: approved for execution on `2026-03-19`.

## Summary

- Goal: implement a deterministic clean-start path for the browser demo environment.
- Subsystem: `scripts`
- Scope of code changes in this milestone:
  - add one reset/bootstrap script for isolated PostgreSQL + Redis + Alembic
  - add one API startup script for the demo runtime
- Out of scope:
  - worker startup
  - search logic changes
  - sync/runtime verification changes
  - README/runbook updates beyond required artifacts

## Inputs

- `docker-compose.yml`
- `.env.staging.example`
- `scripts/run_api.sh`
- `scripts/run_worker.sh`
- current demo planning artifacts:
  - `docs/artifacts/implementation_plan_tomorrow_browser_demo_clean_data.md`
  - `docs/artifacts/tomorrow_browser_demo_checklist.md`

## Deliverables

1. `scripts/reset_demo_env.sh`
   - uses a dedicated compose project name
   - starts isolated PostgreSQL and Redis on demo ports
   - destroys prior demo state
   - waits for health
   - runs `alembic upgrade head`
   - verifies clean row counts for `artists`, `search_cache`, `sync_jobs`
   - verifies Redis `DBSIZE`

2. `scripts/run_demo_api.sh`
   - loads `.env` when present without printing secrets
   - overrides runtime to the isolated demo DB/Redis
   - starts the app on a dedicated demo port
   - reuses `scripts/run_api.sh`

3. required milestone artifacts:
   - `docs/artifacts/walkthrough_demo_runtime_reset_bootstrap.md`

## Defaults

- compose project: `netvrf-demo`
- PostgreSQL host port: `5433`
- Redis host port: `6380`
- API host: `127.0.0.1`
- API port: `8001`
- DB credentials: `netvrf/netvrf`
- DB name: `netvrf`
- app env: `staging`
- reload: `false`
- redis required for health: `true`

## Technical Design

### `reset_demo_env.sh`

- write a temporary compose override file with `!override` port replacement for:
  - `5433:5432`
  - `6380:6379`
- run:
  - `docker compose -p <project> -f docker-compose.yml -f <override> down -v --remove-orphans`
  - `docker compose ... up -d postgres redis`
- wait until:
  - `pg_isready -U netvrf -d netvrf`
  - `redis-cli ping`
- run Alembic against:
  - `DATABASE_URL=postgresql+psycopg://netvrf:netvrf@127.0.0.1:5433/netvrf`
  - `REDIS_URL=redis://127.0.0.1:6380/0`
- verify:
  - `artists` row count
  - `search_cache` row count
  - `sync_jobs` row count
  - Redis `DBSIZE`

### `run_demo_api.sh`

- source `.env` if present using shell export semantics
- override runtime env with the isolated demo values
- set conservative provider timeouts suitable for live demo use
- `exec ./scripts/run_api.sh`

## Acceptance Criteria

- both scripts pass shell syntax validation
- `reset_demo_env.sh` can describe or perform a clean demo reset without printing secrets
- `run_demo_api.sh` resolves to the isolated demo runtime values
- milestone diff remains limited to `scripts` plus required artifacts

## Verification Plan

- `sh -n scripts/reset_demo_env.sh`
- `sh -n scripts/run_demo_api.sh`
- runtime validation if the local environment permits:
  - `./scripts/reset_demo_env.sh`
  - `./scripts/run_demo_api.sh`
  - `curl -i http://127.0.0.1:8001/health`

## Risks

- Compose override must replace, not append, base ports; use `!override`
- local sandbox may block Docker daemon or localhost runtime validation
- source `.env` carefully and never echo token values
