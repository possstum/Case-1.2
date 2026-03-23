# Implementation Plan: Frontend Artist MVP Phase 2 Milestone 4

Status: blocked on `2026-03-19`.

## Summary

- Goal: run a production-like verification of the artist flow against PostgreSQL + Redis + worker, using the real provider tokens already present in `.env`, and capture only milestone artifacts from this work.
- Scope: runtime verification and artifact updates only.
- Out of scope: code changes, broader docs claims, frontend copy tightening.

## Grounded Facts

- `.env` contains non-placeholder `YOUTUBE_MUSIC_TOKEN` and `YANDEX_MUSIC_TOKEN`.
- `.env` must not be shell-sourced because the Yandex token contains shell-special characters.
- `127.0.0.1:8000` is already occupied locally, so the verification app must run on `127.0.0.1:8001`.
- Host ports `5432` and `6379` are already occupied by unrelated Docker containers, so the verification stack must use remapped ports `5433` and `6380`.
- `YouTubeMusicClient.get_*()` is still stubbed. A green sync run may still be partial if Yandex finishes successfully with `mode="catalog_ingest"`.

## Planned Artifact Changes

- create `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_4.md`
- update `docs/artifacts/production_like_verification.md`
- create `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4.md`

## Verification Plan

1. Run focused automated preflight for health/search/entities/web UI/sync jobs and sync/Yandex catalog services.
2. Bring up a fresh isolated PostgreSQL + Redis stack with remapped ports using a temporary Compose override file.
3. Run Alembic migrations with non-secret env overrides and start API plus worker against the same PostgreSQL + Redis runtime.
4. Verify `/health`.
5. Run `/ui` artist search against the ordered query list until one query yields a canonical artist CTA.
6. Capture pre-sync state from `/artists/{id}` and `/ui/artists/{id}`.
7. Enqueue `POST /sync/artist/{id}` and poll `/jobs/{job_id}` until terminal state or timeout.
8. Capture post-sync state from `/artists/{id}` and `/ui/artists/{id}` and confirm Yandex catalog evidence appears.
9. Update production-like verification and walkthrough artifacts with exact commands, results, blockers, and remaining unverified items.

## Acceptance

- `/health` returns `200` with database and Redis both `ok`.
- `/ui` search yields a canonical artist CTA and a concrete `artist_id`.
- `/artists/{id}` and `/ui/artists/{id}` return `200` before sync, with empty Yandex catalog sections on the fresh database.
- `POST /sync/artist/{id}` returns `202` and `/jobs/{job_id}` reaches `finished`.
- the terminal job payload contains a Yandex provider result with `status="updated"`, `mode="catalog_ingest"`, and `catalog_list_count > 0`.
- post-sync `/artists/{id}` and `/ui/artists/{id}` show non-empty Yandex catalog evidence.

## Failure Rules

- any preflight test failure blocks live verification
- inability to get a canonical artist CTA from the ordered live query list blocks the milestone
- sync job `failed`, job timeout, missing Yandex provider result, or zero Yandex catalog list count blocks the milestone
- new defects discovered during verification are recorded as blockers instead of being fixed in this milestone

## Observed Blocker

- The live verification run reached `POST /sync/artist/1`, but the worker crashed before starting the queued job.
- Observed worker failure: `UnicodeDecodeError` while RQ was reading job data from Redis.
- Milestone 4 therefore remains blocked at the worker execution step, and post-sync Yandex catalog proof was not reached.
