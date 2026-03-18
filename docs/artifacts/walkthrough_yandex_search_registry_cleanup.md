# Walkthrough: Yandex Search Registry Cleanup

Status: implemented on `2026-03-18`.

## Scope

- Subsystem changed: search dependency wiring
- Provider client behavior unchanged in this cleanup
- Sync wiring unchanged
- Database schema unchanged

## Why This Follow-Up Was Needed

- The previous auth fix made `YandexMusicClient.search()` work against the public search endpoint without a token
- Search dependency wiring still only instantiated Yandex when `YANDEX_MUSIC_TOKEN` was set
- That behavior no longer matched the provider and could incorrectly disable Yandex search on tokenless runtimes

## What Changed

- Updated `get_optional_provider_registry()` in `app/api/deps.py`
- Yandex search provider is now always included
- YouTube search provider remains token-gated
- Added a narrow regression test that verifies the dependency now returns a registry containing Yandex even when both tokens are unset

## Verification

Commands run:

- `.venv/bin/pytest -q tests/api/test_search.py`
- `.venv/bin/ruff check app/api/deps.py tests/api/test_search.py`

Result:

- `11 passed`
- `ruff check` passed

## Notes

- The old `search_providers_unavailable` path can still happen only if search wiring is explicitly overridden to an empty registry in tests or custom runtime composition.
- This cleanup intentionally does not modify sync registry behavior, which already includes Yandex independently.
