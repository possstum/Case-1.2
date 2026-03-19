# Walkthrough: Demo Runtime Reset And Bootstrap

Status: completed on `2026-03-19`.

## Goal

Implement a deterministic clean-reset and API-start path for the browser demo environment.

## Scope

- `docs/artifacts/implementation_plan_demo_runtime_reset_bootstrap.md`
- `docs/artifacts/walkthrough_demo_runtime_reset_bootstrap.md`
- `scripts/reset_demo_env.sh`
- `scripts/run_demo_api.sh`

Out of scope:

- worker startup
- search logic
- sync flow
- README/runbook updates

## Milestone Log

### Milestone 1: Scripts Baseline

Changed files:

- `docs/artifacts/implementation_plan_demo_runtime_reset_bootstrap.md`
- `docs/artifacts/walkthrough_demo_runtime_reset_bootstrap.md`
- `scripts/reset_demo_env.sh`
- `scripts/run_demo_api.sh`

Commands run:

- `sed -n '1,200p' scripts/run_api.sh`
- `sed -n '1,200p' scripts/run_worker.sh`
- `sed -n '1,220p' docker-compose.yml`
- `sed -n '1,220p' .env.staging.example`
- `rg -n "run_demo|reset_demo|demo env|compose project|search_cache|sync_jobs|flushdb|alembic upgrade head" -S scripts docs README.md app tests`
- `docker compose -f docker-compose.yml -f <temp-override> config`
- `.venv/bin/pytest -q`
- `chmod +x scripts/reset_demo_env.sh scripts/run_demo_api.sh`
- `sh -n scripts/reset_demo_env.sh`
- `sh -n scripts/run_demo_api.sh`
- `./scripts/reset_demo_env.sh`
- `./scripts/run_demo_api.sh`
- `curl -i http://127.0.0.1:8001/health`

Tests run:

- `.venv/bin/pytest -q`
  - result: `105 passed in 5.12s`

Additional verification:

- `sh -n scripts/reset_demo_env.sh`
  - passed
- `sh -n scripts/run_demo_api.sh`
  - passed
- `./scripts/reset_demo_env.sh`
  - passed with isolated compose project `netvrf-demo`
  - Alembic upgraded PostgreSQL cleanly to head
  - row counts after reset:
    - `artists|0`
    - `search_cache|0`
    - `sync_jobs|0`
  - Redis `DBSIZE` after reset: `0`
- `./scripts/run_demo_api.sh`
  - passed after elevated local bind verification
- `curl -i http://127.0.0.1:8001/health`
  - returned `200 OK`
  - payload:
    - `status=ok`
    - `database.status=ok`
    - `redis.status=ok`

Key implementation decisions:

- used a temporary compose override file with `!override` so demo ports replace rather than append to the base compose ports
- fixed demo defaults to isolated ports:
  - PostgreSQL `5433`
  - Redis `6380`
  - API `8001`
- made reset destructive only to the dedicated demo compose project via `down -v --remove-orphans`
- reused `scripts/run_api.sh` for runtime boot so the demo path stays aligned with the real app entrypoint
- sourced `.env` only in the API launcher and did not print secret values

Environment blockers encountered:

- first non-escalated Docker reset attempt failed with Docker daemon socket permission denial
- first non-escalated API bind attempt failed with `operation not permitted` on `127.0.0.1:8001`
- both blockers were environment/sandbox capability issues, not script logic issues
- end-to-end verification succeeded after allowing Docker access and local bind for the demo API

## Final Outcome

- the repository now has a working clean-reset script for isolated demo PostgreSQL + Redis
- the repository now has a working demo API launcher for browser use on `http://127.0.0.1:8001/ui`
- the milestone stayed limited to the `scripts` subsystem plus required artifacts
- worker and sync remain intentionally out of scope for the next milestone
