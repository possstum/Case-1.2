# Implementation Plan: Yandex Search Auth Fix

Status: approved and implemented on `2026-03-18`.

## Summary

- Goal: fix the live Yandex search regression where application-side search fails with `401 Unauthorized` even though the public `api.music.yandex.net/search` endpoint returns `200` when called without auth.
- Scope: minimal provider-layer fix only.
- Non-goal: no sync/catalog ingest changes, no schema changes, no broad search-architecture rewrite.

## Verified Root Cause

The bug is now directly reproduced in two ways:

- direct `curl` to `https://api.music.yandex.net/search?...` without `Authorization` returns `200`
- the same search path through `YandexMusicClient.search()` returns `HTTPError 401`

Current client behavior:

- `YandexMusicClient.search()` returns empty results when no token is configured
- when a token is configured, it calls `_get_json(..., use_auth=True)`
- `_get_json(..., use_auth=True)` sends `Authorization: OAuth <token>`

This behavior is too strict for the search route and breaks live search for a valid public endpoint.

## Proposed Fix

### Milestone 1: Provider Client Fix

Subsystem: `app/providers/yandex_music/*`

- change `YandexMusicClient.search()` so it no longer requires a token
- call `api.music.yandex.net/search` without `Authorization`
- keep the existing auth-capable `_get_json()` path intact for any future/private endpoints
- add regression tests proving that Yandex search:
  - works without a token
  - does not send a `Request` with auth headers on search
  - still respects configured timeout

Acceptance:

- local reproduction path through `YandexMusicClient.search()` no longer raises `401`
- targeted provider tests pass

Status:

- implemented on `2026-03-18`
- `YandexMusicClient.search()` now calls the public search route without `Authorization`
- verified with targeted provider tests and `ruff check`

### Milestone 2: Verification Notes

Subsystem: docs/tests only

- document the root cause and the verified behavior difference between public search and auth-bound requests
- add a walkthrough artifact for the bugfix verification

Acceptance:

- the fix is explained and reproducible from artifacts

Status:

- implemented on `2026-03-18`
- walkthrough artifact created with root-cause summary and verification commands

## Files Expected To Change

- `app/providers/yandex_music/client.py`
- `tests/providers/test_provider_clients.py`
- `docs/artifacts/walkthrough_yandex_search_auth_fix.md`

## Commands Planned

- `.venv/bin/pytest -q tests/providers/test_provider_clients.py tests/providers/test_provider_contracts.py`
- `.venv/bin/ruff check app/providers/yandex_music/client.py tests/providers/test_provider_clients.py`
