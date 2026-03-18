# Implementation Plan: Yandex Music Catalog Ingestion And Segmented Storage

Status: approved on `2026-03-18`; Milestone 1 implemented on `2026-03-18`.

## Summary

- Goal: extend the current provider and storage model so the project can ingest Yandex Music catalog data beyond search hits and persist clearly segmented lists of artists, releases, tracks, tracklists, and artist-facing collections.
- Scope for this plan is Yandex Music only.
- The plan keeps the existing canonical/provider split from `docs/project_brief.md` and avoids a parallel data model unless strictly necessary.
- Release classification must prefer ambiguity over false precision. If Yandex payloads do not expose a reliable release type, the database must preserve the raw source fields and store a nullable normalized classification with confidence.

## Verified Endpoint Matrix

The following routes were verified directly against `api.music.yandex.net` on `2026-03-18` using live HTTP reads.

Working routes:

- `GET /search?text=<query>&type=artist&page=0&page-size=<n>&nocorrect=false`
- `GET /search?text=<query>&type=album&page=0&page-size=<n>&nocorrect=false`
- `GET /search?text=<query>&type=track&page=0&page-size=<n>&nocorrect=false`
- `GET /artists/{artist_id}`
- `GET /artists/{artist_id}/direct-albums`
- `GET /artists/{artist_id}/tracks`
- `GET /artists/{artist_id}/brief-info`
- `GET /albums/{album_id}`
- `GET /albums/{album_id}/with-tracks`
- `GET /tracks/{track_id}`
- `GET /tracks?trackIds=<id[,id2,...]>`

Negative controls:

- `GET /artists/{artist_id}/albums` -> `404`
- `GET /albums/{album_id}/track-ids` -> `404`
- `GET /artists/{artist_id}/not-a-real-route` -> `404`
- `GET /albums/{album_id}/not-a-real-route` -> `404`

## Payload Notes

- `GET /artists/{artist_id}` returns a compound object with `artist`, `albums`, `alsoAlbums`, `popularTracks`, `similarArtists`, `lastReleaseIds`, `lastReleases`, `videos`, `clips`, `vinyls`, and related presentation fields.
- `GET /artists/{artist_id}/brief-info` is similar to the artist detail route and additionally exposes `stats`, `playlistIds`, `playlists`, `links`, and `hasTrailer`.
- `GET /artists/{artist_id}/direct-albums` returns paged album lists under `result.albums`.
- `GET /artists/{artist_id}/tracks` returns paged track lists under `result.tracks`.
- `GET /albums/{album_id}/with-tracks` returns album metadata plus `volumes`, where each volume is an ordered track array.
- Album track ordering is available via nested `albums[].trackPosition.volume` and `albums[].trackPosition.index` on each track item.
- Album payloads expose `metaType`, `year`, `releaseDate`, `trackCount`, `labels`, and availability flags.
- In the sampled payloads, album objects did not expose a reliable explicit source field for `ep` / `lp` / `single`; sampled `metaType` was `music`, and `type` was absent or empty. Normalized segmentation therefore needs a dedicated inference layer with ambiguous fallback.

## Current Model Fit

The repository already has:

- canonical tables for `Artist`, `Release`, `Track`, `ReleaseArtist`, `TrackArtist`, `ReleaseTrack`
- provider snapshot tables for `PlatformArtist`, `PlatformRelease`, `PlatformTrack`, `PlatformReleaseTrack`
- link tables between canonical and provider records

This is a strong base, but it does not yet preserve enough provider-native structure to represent all Yandex list outputs cleanly.

Current gaps:

- no provider-native `release <-> artist` credit table
- no provider-native `track <-> artist` credit table
- no provider-native table for endpoint-produced collections like `direct-albums`, `alsoAlbums`, `popularTracks`, `similarArtists`, `playlists`, `videos`, `vinyls`
- no explicit normalized release segmentation confidence field

## Proposed Data Model

The plan keeps the current canonical/provider split and adds only the provider-side structures needed for full Yandex catalog capture.

### Reuse As-Is

- `platform_artists`
- `platform_releases`
- `platform_tracks`
- `platform_release_tracks`
- canonical tables and link tables

### Add

- `platform_release_artists`
  - purpose: provider-native release credits and release ownership order
  - columns: `platform_release_id`, `platform_artist_id`, `role`, `position`, `raw_json`

- `platform_track_artists`
  - purpose: provider-native track credits and track artist order
  - columns: `platform_track_id`, `platform_artist_id`, `role`, `position`, `raw_json`

- `platform_catalog_lists`
  - purpose: preserve every Yandex collection as a first-class segmented list
  - columns:
    - `platform`
    - `owner_kind` (`artist`, `release`, `track`, `system`)
    - `owner_platform_id`
    - `list_kind` (`direct_albums`, `also_albums`, `popular_tracks`, `similar_artists`, `playlists`, `videos`, `vinyls`, `last_releases`)
    - `source_endpoint`
    - `title`
    - `page`
    - `page_size`
    - `total_items`
    - `raw_json`
    - `fetched_at`

- `platform_catalog_list_items`
  - purpose: ordered membership rows for each stored list
  - columns:
    - `catalog_list_id`
    - `position`
    - `item_kind` (`artist`, `release`, `track`, `playlist`, `video`, `unknown`)
    - `platform_artist_id` nullable
    - `platform_release_id` nullable
    - `platform_track_id` nullable
    - `external_ref` nullable
    - `raw_json`

### Extend Existing Tables

- `platform_releases`
  - keep `release_type` as the normalized field exposed by the app
  - add `release_type_source` nullable string for the raw provider value if present
  - add `release_type_confidence` nullable string with values like `exact`, `heuristic`, `ambiguous`

- `releases`
  - keep `release_type` nullable and only populate it from provider data when confidence is acceptable

## Release Segmentation Policy

Normalized release values should be finite and queryable:

- `album`
- `lp`
- `ep`
- `single`
- `compilation`
- `live`
- `remix`
- `soundtrack`
- `demo`
- `mixtape`
- `other`
- `unknown`

Policy:

- trust a provider-native release class only when it is explicit and stable
- otherwise infer from title markers, track count, and total duration
- if the signal conflicts or is weak, store `unknown` and set confidence to `ambiguous`

## Query Goals

The schema must support simple queries for:

- all releases for an artist
- artist releases segmented by `direct_albums` vs `also_albums`
- all album tracklists with stable order by volume and track index
- all tracks for an artist from `/artists/{id}/tracks`
- all `popular_tracks`, `similar_artists`, `playlists`, and future list kinds from `brief-info`
- releases grouped by normalized `release_type`

## Milestones

### Milestone 1: Provider Contracts Only

Subsystem: `app/providers/yandex_music/*`

- add typed response schemas for artist detail, brief info, direct albums, tracks, and album-with-tracks
- implement read-only `get_artist`, `get_release`, and `get_track`
- add dedicated provider methods for `get_artist_direct_albums`, `get_artist_tracks`, and `get_artist_brief_info`
- do not change DB in this milestone

Acceptance:

- provider client can fetch and parse the verified routes above
- tests cover `200` mapping from saved fixtures

Status:

- implemented on `2026-03-18`
- verified with targeted provider tests and `ruff check`

### Milestone 2: Database Schema Only

Subsystem: `app/db/models/*` + `alembic/*`

- add `platform_release_artists`
- add `platform_track_artists`
- add `platform_catalog_lists`
- add `platform_catalog_list_items`
- extend `platform_releases` with release segmentation fields

Acceptance:

- SQLite WAL and PostgreSQL migrations both succeed
- ORM relationships load without circular breakage

Status:

- implemented on `2026-03-18`
- verified on SQLite via `tests/db`
- PostgreSQL DDL compile is covered by `tests/db/test_schema_compile.py`
- direct local PostgreSQL container verification was attempted but blocked because local port `5432` was already allocated

### Milestone 3: Ingestion And Upsert Service

Subsystem: `app/services/*`

- add a Yandex catalog ingestion service that upserts provider artists, releases, tracks, credits, tracklists, and catalog lists
- preserve raw provider payloads
- keep normalization conservative

Acceptance:

- one ingest call for an artist stores direct albums, popular tracks, similar artists, and related entities idempotently

Status:

- implemented on `2026-03-18`
- verified with targeted service tests
- service currently ingests provider-side graph only; sync wiring stays for Milestone 4

### Milestone 4: Sync Job Wiring

Subsystem: `app/tasks/*` and sync orchestration

- wire Yandex provider detail ingestion into `SyncService`
- choose a bounded sync strategy so one sync does not explode into uncontrolled recursive crawling

Acceptance:

- sync job fetches and stores one artist graph deterministically

Status:

- implemented on `2026-03-18`
- verified with targeted sync service and sync API tests
- sync wiring now uses Yandex catalog ingest for Yandex-linked targets while preserving provider-entity refresh for other providers

### Milestone 5: Verification And Read Model Polish

Subsystem: tests and docs only

- add regression tests
- update docs and walkthrough
- document recommended SQL queries or admin read paths for segmented browsing

Acceptance:

- the new storage layout is queryable and explained

Status:

- implemented on `2026-03-18`
- verified with targeted sync-service and catalog-service regression tests
- README now includes concrete SQL query recipes for segmented Yandex catalog browsing

## Non-Goals

- no YouTube expansion in this task
- no attempt to ingest the entire Yandex catalog globally
- no destructive rebuild of the current canonical model
- no hardcoded credentials or token logging

## Commands For Milestone 0 Research

Used during planning:

- `curl https://api.music.yandex.net/search?...`
- `curl https://api.music.yandex.net/artists/{id}`
- `curl https://api.music.yandex.net/artists/{id}/direct-albums`
- `curl https://api.music.yandex.net/artists/{id}/tracks`
- `curl https://api.music.yandex.net/artists/{id}/brief-info`
- `curl https://api.music.yandex.net/albums/{id}`
- `curl https://api.music.yandex.net/albums/{id}/with-tracks`
- `curl https://api.music.yandex.net/tracks/{id}`

## Approval Request

Recommended first implementation slice:

1. Milestone 1 only
2. then Milestone 2

This keeps provider parsing separate from schema migration and follows the one-subsystem-per-milestone rule.
