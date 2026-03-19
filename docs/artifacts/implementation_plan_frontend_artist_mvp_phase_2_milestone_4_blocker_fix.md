# Implementation Plan: Frontend Artist MVP Phase 2 Milestone 4 Blocker Fix

Status: in progress on `2026-03-19`.

## Summary

- Goal: remove the queue/worker blocker that makes the RQ worker crash while reading queued jobs from Redis, then rerun production-like verification for the artist sync flow.
- Scope: queue/worker integration only, minimal regression tests, blocker-specific artifacts, and repeated production-like verification.
- Out of scope: frontend copy, shared docs claims, provider behavior changes, search UX changes, and unrelated dirty files.

## Grounded Facts

- The previous production-like run reached `POST /sync/artist/1`, created an RQ job, and left `/jobs/{job_id}` stuck at `queued`.
- The worker crashed before starting the job with `UnicodeDecodeError` while reading job data from Redis.
- `app/tasks/queue.py` currently builds the RQ Redis connection with `decode_responses=True`.
- RQ stores pickled/binary job payloads in Redis hashes, so forced UTF-8 response decoding is not safe on the worker path.
- `app/db/session.py` separately creates the API Redis client with `decode_responses=True`; that path powers health checks and rate limiting and is outside this blocker fix.
- Runtime assumptions for the rerun stay fixed:
  - `APP_PORT=8001`
  - PostgreSQL host port `5433`
  - Redis host port `6380`
  - real provider tokens come from `.env` and must not be printed or logged

## Files In Scope

- `app/tasks/queue.py`
- `tests/tasks/test_queue.py`
- `docs/artifacts/production_like_verification.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_blocker_fix.md`

## Planned Changes

1. Update the RQ Redis connection factory in `app/tasks/queue.py` to use `decode_responses=False`.
2. Keep the queue scheduler interface and queue naming unchanged.
3. Add compact regression coverage for:
   - binary-safe Redis connection creation
   - `get_queue()` wiring
   - `RQSyncJobScheduler.schedule()` enqueue target and argument passing
   - `create_worker()` default queue wiring and binary-safe connection usage
4. Rerun targeted queue/worker/sync tests.
5. Rerun the production-like verification flow against PostgreSQL + Redis + worker and capture exact evidence.

## Acceptance

- The worker no longer crashes while reading the queued job from Redis.
- `POST /sync/artist/{id}` creates a job and the worker actually consumes it.
- `/jobs/{job_id}` leaves `queued` and reaches a terminal state.
- The terminal payload contains a Yandex provider result with:
  - `status="updated"`
  - `mode="catalog_ingest"`
  - `catalog_list_count > 0`
- Post-sync `GET /artists/{id}` returns non-empty `yandex_catalog_sections`.
- Post-sync `GET /ui/artists/{id}` shows Yandex native catalog evidence.

## Failure Rules

- Any targeted test failure blocks live verification.
- If `Krovostok` no longer yields a canonical artist CTA, record the exact evidence as a new blocker instead of widening the query set.
- If the worker crashes again, record the exact traceback and final `/jobs/{job_id}` payload as a new blocker.
- If the job reaches `failed`, record the exact `error_json` and provider result payload as blocker evidence.
- If the job reaches `finished` but post-sync Yandex catalog evidence is still absent, record the exact API/UI proof as a new blocker.

## Verification Flow

1. Start isolated PostgreSQL + Redis with remapped ports `5433` and `6380`.
2. Apply migrations against PostgreSQL.
3. Start the API on `127.0.0.1:8001`.
4. Start the RQ worker against the same Redis instance.
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

- compact queue/worker-only code diff
- targeted test command and result
- updated `docs/artifacts/production_like_verification.md`
- new `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_blocker_fix.md`
