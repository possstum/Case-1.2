# Walkthrough: Yandex Catalog Milestone 4

Status: implemented on `2026-03-18`.

## Scope

- Subsystem changed: sync orchestration and job wiring
- Database schema unchanged
- Provider contracts unchanged

## What Changed

- Extended `SyncService` with an optional `YandexCatalogIngestionService`
- Yandex-linked sync targets now use bounded catalog ingest instead of the old single-entity refresh path
- Non-Yandex providers still use the existing `get_*()` plus `LinkService.persist_platform_entity(...)` flow
- Updated FastAPI dependency wiring so sync execution builds one shared `LinkService` and one Yandex ingestion service instance
- Updated RQ worker job wiring in `app/tasks/sync_jobs.py` to use the same sync composition
- Sync provider registry now always includes `YandexMusicClient` for detail/list refreshes, even when the search token is absent
- Search provider registry behavior stays unchanged and remains token-gated

## Verification

Commands run:

- `.venv/bin/pytest -q tests/services/test_sync_service.py tests/services/test_yandex_catalog_service.py tests/api/test_sync_jobs.py`
- `.venv/bin/ruff check app/services/sync_service.py app/api/deps.py app/tasks/sync_jobs.py tests/services/test_sync_service.py`

Result:

- `9 passed`
- `ruff check` passed

## Notes

- The bounded strategy is still deterministic: Yandex artist sync enters the provider-native catalog ingest path, while release and track sync keep the same one-target entrypoint semantics.
- This milestone intentionally does not add new read APIs; it only wires background refresh execution to the storage added in Milestones 2 and 3.
