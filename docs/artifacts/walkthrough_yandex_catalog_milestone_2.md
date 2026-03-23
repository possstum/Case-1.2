# Walkthrough: Yandex Catalog Milestone 2

Status: implemented on `2026-03-18`.

## Scope

- Subsystem changed: `app/db/models/*` and `alembic/*`
- Provider code unchanged
- Service and sync layers unchanged

## What Changed

- Extended `platform_releases` with:
  - `release_type_source`
  - `release_type_confidence`
- Added provider-native credit tables:
  - `platform_release_artists`
  - `platform_track_artists`
- Added provider-native list storage:
  - `platform_catalog_lists`
  - `platform_catalog_list_items`
- Updated ORM exports in `app/db/models/__init__.py`
- Added a delta Alembic revision above the current head
- Made the new Alembic revision idempotent to coexist with the repo's bootstrap migration pattern based on `Base.metadata.create_all()`

## Verification

Commands run:

- `.venv/bin/pytest -q tests/db`
- `.venv/bin/ruff check app/db/models alembic/versions/1c2d3e4f5a6b_yandex_catalog_storage.py tests/db/test_migrations.py`
- `docker compose up -d postgres`
- `docker compose down`

Result:

- `tests/db`: `9 passed`
- `ruff check`: passed
- live PostgreSQL container verification did not complete because port `5432` was already allocated locally
- PostgreSQL DDL compilation is still covered by `tests/db/test_schema_compile.py`

## Notes

- The new migration intentionally checks for existing tables and columns before creating them.
- This keeps fresh bootstrap upgrades safe because the earlier bootstrap revision creates tables from current metadata.
