# Walkthrough: Yandex Search Auth Fix

Status: implemented on `2026-03-18`.

## Scope

- Subsystem changed: `app/providers/yandex_music/*`
- Search architecture unchanged
- Sync/catalog ingest unchanged
- Database schema unchanged

## Root Cause

- Direct `curl` to `https://api.music.yandex.net/search?...` without `Authorization` returned `200`
- The same search path through `YandexMusicClient.search()` returned `HTTPError 401`
- The previous client implementation only searched when a token was present and sent `Authorization: OAuth <token>` for `/search`
- For the verified live Yandex search route, this auth header was the cause of the failure

## What Changed

- Removed the token gate from `YandexMusicClient.search()`
- Changed Yandex search requests to call the public `/search` route without `Authorization`
- Kept the auth-capable `_get_json(..., use_auth=True)` behavior intact for any future/private endpoint usage
- Added regression tests that prove:
  - Yandex search still uses the configured timeout
  - Yandex search does not send auth headers even when a token is configured
  - Yandex search works without a token

## Verification

Commands run:

- `.venv/bin/pytest -q tests/providers/test_provider_clients.py tests/providers/test_provider_contracts.py`
- `.venv/bin/ruff check app/providers/yandex_music/client.py tests/providers/test_provider_clients.py`

Result:

- `12 passed`
- `ruff check` passed

## Notes

- This fix addresses the reproduced live-search regression only.
- Search dependency wiring still decides independently whether to instantiate providers; this patch only makes the Yandex client behave correctly once used.
