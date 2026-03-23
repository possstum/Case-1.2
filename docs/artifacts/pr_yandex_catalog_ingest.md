# PR Draft: Add Yandex Catalog Ingest Storage And Wire Sync Refresh Through It

## Title

`Add Yandex catalog ingest storage and wire sync refresh through it`

## Description

```md
## Summary
This PR makes Yandex-backed refresh reviewable by adding provider-native catalog storage, wiring Yandex sync to catalog ingest, and aligning Yandex search wiring with the verified public search behavior.

## In scope
- add Yandex catalog storage tables and ORM models
- add typed Yandex detail/list payload parsing
- add `YandexCatalogIngestionService` for artist/release/track ingest
- route Yandex-linked sync jobs through catalog ingest while leaving non-Yandex providers on the existing entity refresh path
- align search dependency wiring so public Yandex search is available without `YANDEX_MUSIC_TOKEN`
- add regression coverage for provider parsing, migrations, sync execution, and `/ui`/search wiring

## Verification
- `ruff check .`
- `pytest -q`
- local baseline green
- staging-like smoke already recorded separately
- production-like verification with real tokens is intentionally out of scope for this PR

## Reviewer focus
- migration safety on SQLite/PostgreSQL
- correctness of Yandex catalog upsert/idempotency
- sync job result semantics for partial provider success
- tokenless Yandex search behavior and absence of auth on public search

## Out of scope
- production-like verification with real tokens
- docs claims about production-like readiness
- implementing `YouTubeMusicClient.get_*()`
- implementing `app/tasks/search_jobs.refresh_search_cache`
```
