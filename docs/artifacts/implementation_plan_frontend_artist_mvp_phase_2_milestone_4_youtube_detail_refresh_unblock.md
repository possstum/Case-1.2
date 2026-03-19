# Implementation Plan: Frontend Artist MVP Phase 2 Milestone 4 YouTube Detail Refresh Unblock

Status: approved and ready for implementation on `2026-03-19`.

## Summary

- Goal: remove the remaining `partial=true` blocker in the artist sync flow by implementing YouTube detail refresh for already-linked entities.
- Scope: `app/providers/youtube_music/client.py`, targeted regressions in `tests/providers/test_provider_clients.py` and `tests/services/test_sync_service.py`, plus milestone artifacts only.
- Out of scope: Yandex code, frontend/UI code or copy, queue/worker code, DB schema, README, `docs/project_brief.md`, and the already-dirty `docs/artifacts/production_like_verification.md`.

## Grounded Facts

- `YouTubeMusicClient.get_artist()`, `get_release()`, and `get_track()` still raise `NotImplementedError`.
- `SyncService.execute()` already computes `partial` from provider update count, so no sync-service logic change is required to reach `partial=false`.
- The current targeted baseline is green before changes:
  - `.venv/bin/python -m pytest -q tests/providers/test_provider_clients.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py tests/api/test_sync_jobs.py`
  - result: `32 passed`
- Pre-edit live probe findings with the real YouTube token loaded from `.env`:
  - `channels.list` for `UCi-dSgoZzJRuV5AWDkQi9zA` returned `200` with one item and `snippet.title`
  - `videos.list` returned `200` with one item and `contentDetails.duration`
  - `playlists.list` with a dummy id returned `200` and `items=[]`, so playlist mapping will stay aligned to the documented Google shape and be locked by targeted tests

## Public APIs And Interfaces

- No external API response, route, or schema changes.
- Internal provider behavior only:
  - `app/providers/youtube_music/client.py` detail methods will return real provider entities instead of raising.
  - YouTube detail refresh `raw_json` will be normalized to the fields current services already read: `url`, `artist_names`, `track_count`, `duration_ms`, `release_title`, and `track_number` when known.
- Conservative defaults:
  - do not infer `release_type`
  - do not infer `release_title`
  - do not infer `track_number`
  - leave unknown fields as `None`

## Milestone 0: Artifact Bootstrap

Files to create:

- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_4_youtube_detail_refresh_unblock.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_youtube_detail_refresh_unblock.md`

Artifact requirements:

- record goal, scope, stop conditions, command matrix, and acceptance matrix
- note that `tests/providers/test_provider_clients.py` and `tests/services/test_sync_service.py` are already dirty and must be edited surgically

## Milestone 1: YouTube Provider Detail Refresh

Files to change:

- `app/providers/youtube_music/client.py`

Implementation details:

- replace the single search endpoint constant with dedicated search, channels, playlists, and videos endpoints
- add one shared helper for Google list responses that:
  - uses the existing `key=<token>` auth model
  - returns exactly one usable item
  - raises `ValueError` for missing or unusable `items`
- implement `get_artist()` with `channels.list?part=snippet&id=...`
- implement `get_release()` with `playlists.list?part=snippet,contentDetails&id=...`
- implement `get_track()` with `videos.list?part=snippet,contentDetails&id=...`
- add a small local ISO-8601 duration parser for `contentDetails.duration`
- keep the diff local to the YouTube provider client

## Milestone 2: Targeted Regression Tests

Files to change:

- `tests/providers/test_provider_clients.py`
- `tests/services/test_sync_service.py`

Targeted tests:

- success-path provider tests for YouTube artist, release, and track detail methods
- regression for empty `items[]` raising `ValueError`
- duration parser regression proving `PT3M05S -> 185000`
- malformed duration regression proving `duration_ms=None`
- sync regression confirming full-success artist sync returns:
  - `updated_count == 2`
  - `partial is False`
  - YouTube `status="updated"` with `mode="entity_refresh"`
  - Yandex `status="updated"` with `mode="catalog_ingest"`
- keep the existing partial-success regression where YouTube fails and Yandex succeeds

Planned commands:

- `.venv/bin/python -m pytest -q tests/providers/test_provider_clients.py tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py tests/api/test_sync_jobs.py`
- `.venv/bin/ruff check app/providers/youtube_music/client.py tests/providers/test_provider_clients.py tests/services/test_sync_service.py`

## Milestone 3: Production-Like Verification

Files to update:

- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_youtube_detail_refresh_unblock.md`

Verification environment:

- `APP_PORT=8001`
- PostgreSQL on `5433`
- Redis on `6380`
- real provider tokens loaded from `.env` via `dotenv_values`
- no shell-sourcing `.env`
- no logging of `Authorization`, `Cookie`, `Token`, or YouTube `key`

Verification flow:

- reuse the same PostgreSQL + Redis + worker setup as the prior production-like milestone
- verify `/health`
- `GET /ui?q=Krovostok&kind=artist&limit=5`
- confirm selected artist still links to Yandex `218095` and YouTube `UCi-dSgoZzJRuV5AWDkQi9zA`
- `POST /sync/artist/{id}`
- poll `/jobs/{job_id}` to terminal state
- re-check `/artists/{id}` and `/ui/artists/{id}`

Acceptance:

- `/jobs/{job_id}` reaches `finished`
- terminal payload contains both providers with `status="updated"`
- YouTube provider result has `mode="entity_refresh"`
- Yandex provider result has `mode="catalog_ingest"` and `catalog_list_count > 0`
- terminal payload has `partial=false`
- post-sync `/artists/{id}` still returns non-empty `yandex_catalog_sections`
- post-sync `/ui/artists/{id}` still shows `Yandex native catalog`
- no regression in the Yandex live sync path

## Assumptions And Defaults

- Search behavior remains unchanged; this follow-up is detail refresh only.
- Existing unrelated dirty files remain untouched.
- If live verification fails for Yandex, queue/worker, or selection drift, record exact evidence and stop without widening the code diff.
