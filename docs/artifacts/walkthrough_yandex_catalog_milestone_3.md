# Walkthrough: Yandex Catalog Milestone 3

Status: implemented on `2026-03-18`.

## Scope

- Subsystem changed: `app/services/*`
- Database schema unchanged
- Sync wiring unchanged

## What Changed

- Added `YandexCatalogIngestionService`
- Added `YandexCatalogIngestionSummary`
- Implemented bounded artist-graph ingestion:
  - artist detail
  - artist brief info
  - direct albums
  - artist tracks
  - album tracklists for direct albums
- Reused `LinkService` for provider entity upserts
- Added service-side replacement logic for:
  - `platform_release_artists`
  - `platform_track_artists`
  - `platform_release_tracks`
  - `platform_catalog_lists`
  - `platform_catalog_list_items`
- Added conservative release classification handling:
  - exact when provider gives an explicit supported type
  - heuristic for title markers like `EP`
  - `unknown` with `ambiguous` confidence otherwise

## Verification

Commands run:

- `.venv/bin/pytest -q tests/services/test_yandex_catalog_service.py tests/services/test_sync_service.py tests/services/test_matching_service.py tests/services/test_matching_config.py`
- `.venv/bin/ruff check app/services app/services/yandex_catalog_service.py tests/services/test_yandex_catalog_service.py`

Result:

- `10 passed`
- `ruff check` passed

## Notes

- The service is idempotent for the tested artist graph because it replaces provider-native credits, tracklists, and catalog-list memberships on refresh instead of appending.
- Sync/job integration is intentionally untouched in this milestone and belongs to Milestone 4.
