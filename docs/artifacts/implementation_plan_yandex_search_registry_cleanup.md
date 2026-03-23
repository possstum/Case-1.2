# Implementation Plan: Yandex Search Registry Cleanup

Status: approved and implemented on `2026-03-18`.

## Summary

- Goal: align search dependency wiring with the verified Yandex provider behavior after the auth fix.
- Scope: search provider registry only.
- Non-goals:
  - no sync wiring changes
  - no provider client behavior changes
  - no schema, service, or matching changes

## Verified Context

- `YandexMusicClient.search()` now works against the public `api.music.yandex.net/search` route without auth
- search dependency wiring in `app/api/deps.py` still adds Yandex only when `YANDEX_MUSIC_TOKEN` is present
- this no longer matches the provider behavior and can incorrectly disable Yandex search on a tokenless runtime

## Proposed Change

### Milestone 1: Search Wiring Only

Subsystem: `app/api/deps.py`

- update `get_optional_provider_registry()` so it always includes `YandexMusicClient(...)`
- keep YouTube token-gated as-is
- preserve the existing `None` return only when both:
  - YouTube is unavailable because there is no key
  - Yandex is explicitly not desired no longer applies, so registry should now be non-empty by default
- no changes to sync wiring in this fix

Acceptance:

- search runtime can instantiate Yandex provider without `YANDEX_MUSIC_TOKEN`
- no behavior change for YouTube provider gating

Status:

- implemented on `2026-03-18`
- `get_optional_provider_registry()` now always includes `YandexMusicClient(...)`
- YouTube provider remains token-gated
- verified with targeted search API tests and `ruff check`

### Milestone 2: Verification

Subsystem: tests/docs only

- add a narrow regression test for the dependency behavior
- add a walkthrough artifact with commands and rationale

Acceptance:

- targeted tests pass
- the cleanup is documented and reproducible

Status:

- implemented on `2026-03-18`
- walkthrough artifact created

## Files Expected To Change

- `app/api/deps.py`
- one targeted test file under `tests/api/*` or `tests/services/*`
- `docs/artifacts/walkthrough_yandex_search_registry_cleanup.md`

## Commands Planned

- `.venv/bin/pytest -q <targeted tests>`
- `.venv/bin/ruff check app/api/deps.py <targeted tests>`
