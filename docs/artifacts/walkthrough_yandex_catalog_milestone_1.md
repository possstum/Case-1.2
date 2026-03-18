# Walkthrough: Yandex Catalog Milestone 1

Status: implemented on `2026-03-18`.

## Scope

- Subsystem changed: `app/providers/yandex_music/*`
- Database schema unchanged
- Sync orchestration unchanged

## What Changed

- Added typed provider-side response models for:
  - artist detail
  - artist brief info
  - artist direct albums
  - artist tracks
  - album with tracks
  - shared pager and collection items
- Implemented read-only Yandex detail methods:
  - `get_artist()`
  - `get_release()`
  - `get_track()`
- Implemented Yandex list/detail helpers:
  - `get_artist_detail()`
  - `get_artist_brief_info()`
  - `get_artist_direct_albums()`
  - `get_artist_tracks()`
  - `get_release_with_tracks()`
- Kept `/search` behavior unchanged: it still requires a configured token before live fan-out.
- Detail/list fetches use public Yandex Music routes without forcing `Authorization` headers.

## Mapping Decisions

- Artist aliases are collected conservatively from `decomposed` and `dbAliases`.
- Release `type` is passed through only when the payload explicitly provides it.
- Track ordering is derived from `trackPosition` or nested `albums[].trackPosition`.
- Track `release_title` falls back to the first nested album title, or the surrounding album title for `with-tracks`.

## Verification

Commands run:

- `.venv/bin/pytest -q tests/providers/test_provider_clients.py tests/providers/test_provider_mappers.py tests/providers/test_provider_contracts.py`
- `.venv/bin/ruff check app/providers/yandex_music tests/providers/test_provider_clients.py`

Result:

- `13 passed`
- `ruff check` passed
