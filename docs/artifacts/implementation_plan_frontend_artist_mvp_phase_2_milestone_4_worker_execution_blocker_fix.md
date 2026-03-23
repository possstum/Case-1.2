# Implementation Plan: Frontend Artist MVP Phase 2 Milestone 4 Worker Execution Blocker Fix

Status: in progress on `2026-03-19`.

## Summary

- Goal: remove the worker execution blocker that now happens after the Redis decode fix, then rerun the production-like artist sync flow until either the milestone turns green or a new blocker is captured with exact evidence.
- Scope: worker execution subsystem only, minimal regression tests, blocker-specific artifacts, and repeated production-like verification.
- Out of scope: queue serialization changes, provider behavior changes, frontend copy, shared docs claims, and unrelated dirty files.

## Grounded Facts

- The previous blocker fix changed the RQ Redis connection to `decode_responses=False` and removed the `UnicodeDecodeError` while reading queued jobs from Redis.
- In the latest production-like rerun, the worker successfully dequeued `app.tasks.sync_jobs.run_sync_job(...)`.
- The next failure happened in the RQ work-horse process on macOS:
  - `+[NSCharacterSet initialize] ... fork() was called`
  - `Work-horse terminated unexpectedly; waitpid returned 6 (signal 6)`
- The app database never observed a `started` or terminal `sync_jobs` state, which means sync application logic did not get far enough to update the row.
- Installed `rq==1.16.2` provides `SimpleWorker`, which executes jobs in-process without the forked work-horse step.
- Runtime assumptions remain fixed:
  - `APP_PORT=8001`
  - PostgreSQL host port `5433`
  - Redis host port `6380`
  - real provider tokens come from `.env` and must not be printed or logged

## Files In Scope

- `app/tasks/worker.py`
- `tests/tasks/test_queue.py`
- `docs/artifacts/production_like_verification.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_worker_execution_blocker_fix.md`

## Planned Changes

1. Make worker class selection platform-aware in `app/tasks/worker.py`.
2. Keep standard `rq.Worker` on non-macOS platforms.
3. Use `rq.SimpleWorker` on macOS to avoid the forked work-horse path that crashes locally.
4. Add regression coverage for:
   - worker class selection on macOS vs non-macOS
   - default queue wiring
   - shared binary-safe Redis connection usage
5. Rerun targeted worker/queue/sync tests.
6. Rerun the full production-like verification flow.

## Acceptance

- The local production-like worker no longer crashes in the macOS work-horse path.
- `POST /sync/artist/{id}` creates a job that the worker actually executes.
- `/jobs/{job_id}` reaches a terminal state.
- The terminal payload contains a Yandex provider result with:
  - `status="updated"`
  - `mode="catalog_ingest"`
  - `catalog_list_count > 0`
- Post-sync `GET /artists/{id}` returns non-empty `yandex_catalog_sections`.
- Post-sync `GET /ui/artists/{id}` shows Yandex native catalog evidence.

## Failure Rules

- Any targeted test failure blocks live verification.
- If the worker now reaches sync execution but the job ends in `failed`, record the exact `error_json` and provider result payload as the new blocker.
- If the worker reaches `finished` but Yandex catalog evidence is still absent, record the exact API/UI proof as the new blocker.
- If another runtime platform issue appears before sync execution, capture the exact traceback/log and stop widening the diff.

## Verification Flow

1. Start isolated PostgreSQL + Redis with `5433` and `6380`.
2. Apply migrations against PostgreSQL.
3. Start the API on `127.0.0.1:8001`.
4. Start the worker with the updated execution strategy.
5. Verify:
   - `GET /health`
   - `GET /ui` artist search
   - `GET /artists/{id}`
   - `GET /ui/artists/{id}`
   - `POST /sync/artist/{id}`
   - polling `GET /jobs/{job_id}`
   - post-sync `GET /artists/{id}`
   - post-sync `GET /ui/artists/{id}`

## Milestone Output

- compact worker-execution-only code diff
- targeted test command and result
- updated `docs/artifacts/production_like_verification.md`
- new `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_worker_execution_blocker_fix.md`
