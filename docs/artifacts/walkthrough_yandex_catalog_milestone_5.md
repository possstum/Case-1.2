# Walkthrough: Yandex Catalog Milestone 5

Status: implemented on `2026-03-18`.

## Scope

- Subsystem changed: tests and docs only
- Production code unchanged
- Database schema unchanged

## What Changed

- Added sync regression tests for Yandex `release` and `track` catalog-ingest branches
- Added a query-level regression test that exercises the new storage layout through representative segmented reads:
  - all releases for an artist
  - `direct_albums`
  - `artist_tracks`
  - ordered album tracklists
  - release grouping by normalized `release_type`
- Added a README cookbook with SQL read recipes for the new Yandex catalog tables
- Updated the implementation plan artifact with Milestone 5 status

## Verification

Commands run:

- `.venv/bin/pytest -q tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py`
- `.venv/bin/ruff check tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py`

Result:

- `8 passed`
- `ruff check` passed

## Notes

- This milestone intentionally avoids adding a new HTTP/admin API for segmented catalog reads. The documented supported read path remains direct SQL against the provider-side tables.
- The README query cookbook uses provider IDs because `platform_catalog_lists.owner_platform_id` and related provider-native tables are keyed by provider identifiers rather than canonical IDs.
