# Implementation Plan: Frontend Artist MVP Phase 2 Milestone 4 Yandex 403 Fix

Status: approved and ready for implementation on `2026-03-19`.

## Summary

- Goal: unblock the live artist sync flow by fixing the Yandex catalog/detail request path so Yandex can complete `catalog_ingest` successfully even when YouTube `get_*()` still fails.
- Scope: Yandex provider/catalog-ingest subsystem only, plus targeted regression tests and milestone artifacts.
- Out of scope: frontend copy, shared docs claims, YouTube implementation, schema changes, queue/worker changes, and unrelated dirty files.

## Grounded Facts

- `SyncService.execute()` already finishes a job when at least one provider updates; it only marks `provider_refresh_failed` when `updated_count == 0`.
- The current live blocker is in the Yandex path: the last production-like run reached terminal state but failed because Yandex `provider_id=218095` returned `HTTP Error 403: Forbidden`.
- Current Yandex client behavior is asymmetric:
  - `/search` is intentionally public and must stay unauthenticated.
  - catalog/detail methods currently call public routes without auth.
- The configured Yandex token in `.env` is a callback-style value with extra `&token_type=...` metadata appended. If used raw in `Authorization`, it would be malformed.
- Current targeted baseline is green before changes:
  - `.venv/bin/python -m pytest -q tests/providers/test_provider_clients.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py`
  - result: `19 passed`

## Public APIs And Interfaces

- No external API or schema contract changes.
- Internal provider behavior changes only:
  - `app/providers/yandex_music/client.py` gains normalized OAuth token handling.
  - Yandex catalog/detail routes use `public-first, auth-retry-on-401/403`.
  - `search()` remains unauthenticated.

## Milestone 0: Plan Artifact

Files to create:

- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_4_yandex_403_fix.md`

Acceptance:

- The root-cause hypothesis, chosen auth strategy, targeted test matrix, and verification flow are documented before code changes.

## Milestone 1: Yandex Provider Auth Recovery

Files to change:

- `app/providers/yandex_music/client.py`
- `tests/providers/test_provider_clients.py`
- `tests/services/test_sync_service.py`

Implementation details:

- Add a private token-normalization helper in `YandexMusicClient`.
- Normalization rules:
  - trim whitespace
  - strip leading `OAuth ` or `Bearer ` if present
  - if the value contains `access_token=...`, parse and use that value
  - otherwise, if the value contains callback metadata like `&token_type=`, `&expires_in=`, or `&cid=`, keep only the first segment before `&`
  - return `None` for empty results
- Replace the current boolean auth switch with an explicit per-request policy:
  - `search`: single public request, never send auth
  - catalog/detail routes: try the public request first; if it fails with `401` or `403` and a normalized token exists, retry once with `Authorization: OAuth <normalized_token>`
- Apply the retry policy to every route used by artist sync:
  - `get_artist_detail`
  - `get_artist_brief_info`
  - `get_artist_direct_albums`
  - `get_artist_tracks`
  - `get_release`
  - `get_release_with_tracks`
  - `get_track`
- Keep `SyncService` logic unchanged and add a regression test that locks the existing partial-success contract.

Targeted tests:

- provider client retries `get_artist()` with OAuth after public `403`
- OAuth retry uses the normalized token, not the raw callback-style string
- search still sends no auth even when a token is configured
- sync finishes with `status="finished"` and `partial=true` when YouTube fails but Yandex catalog ingest succeeds

Planned command:

- `.venv/bin/python -m pytest -q tests/providers/test_provider_clients.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py tests/api/test_sync_jobs.py`

Milestone artifact:

- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_yandex_403_fix.md`

## Milestone 2: Production-Like Verification

Files to change:

- `docs/artifacts/production_like_verification.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_yandex_403_fix.md`

Verification flow:

- use PostgreSQL on `5433`
- use Redis on `6380`
- run API on `127.0.0.1:8001`
- run worker against the same DB/Redis
- load real provider tokens from `.env` through process env injection without printing values and without shell-sourcing `.env`
- reuse the same artist-sync path as the last blocker run:
  - `GET /ui?q=Krovostok&kind=artist&limit=5`
  - select the primary canonical artist
  - confirm the linked Yandex provider id is still `218095` before sync; if it is not, record selection drift and stop
  - `POST /sync/artist/{id}`
  - poll `GET /jobs/{job_id}` to terminal state
  - verify post-sync `GET /artists/{id}`
  - verify post-sync `GET /ui/artists/{id}`

Acceptance:

- `/jobs/{job_id}` reaches `finished`
- the terminal payload contains a Yandex provider result with:
  - `status="updated"`
  - `mode="catalog_ingest"`
  - `catalog_list_count > 0`
- the terminal payload may still include a failed YouTube provider result
- post-sync `/artists/{id}` returns non-empty `yandex_catalog_sections`
- post-sync `/ui/artists/{id}` contains `Yandex native catalog`

## Assumptions And Defaults

- `public-first, auth-retry-on-401/403` is the chosen default because it preserves the verified public-search behavior while fixing live catalog/detail failures with the smallest diff.
- No changes will be made to `app/services/sync_service.py` unless targeted tests prove the existing partial-success contract is wrong.
- Existing unrelated modified files in the worktree remain untouched.
- If Yandex still fails after normalized OAuth retry, implementation stops at blocker capture and records the exact failing endpoint and status instead of widening scope into YouTube or frontend work.
