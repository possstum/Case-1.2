# Walkthrough: Yandex Music Endpoint Research

Status: research-only walkthrough on `2026-03-18`.

## What Was Verified

- Search endpoints work:
  - `GET /search?text=<query>&type=artist&page=0&page-size=<n>&nocorrect=false`
  - `GET /search?text=<query>&type=album&page=0&page-size=<n>&nocorrect=false`
  - `GET /search?text=<query>&type=track&page=0&page-size=<n>&nocorrect=false`
- Core detail endpoints work:
  - `GET /artists/{artist_id}`
  - `GET /artists/{artist_id}/direct-albums`
  - `GET /artists/{artist_id}/tracks`
  - `GET /artists/{artist_id}/brief-info`
  - `GET /albums/{album_id}`
  - `GET /albums/{album_id}/with-tracks`
  - `GET /tracks/{track_id}`
  - `GET /tracks?trackIds=<id[,id2,...]>`

## Negative Controls

- `GET /artists/{artist_id}/albums` returned `404`
- `GET /albums/{album_id}/track-ids` returned `404`
- synthetic fake routes returned `404`

## Payload Findings

- Artist detail and brief-info return collection sections such as `albums`, `alsoAlbums`, `popularTracks`, `similarArtists`, `playlists`, `videos`, and `vinyls`.
- Album tracklists come from `volumes`, not from a flat top-level track array.
- Track order is available through nested `albums[].trackPosition.volume` and `albums[].trackPosition.index`.
- Sampled album payloads did not expose a stable explicit `ep` / `lp` / `single` field, so release segmentation must remain conservative.

## Consequence For Schema

- Existing provider snapshot tables are useful but insufficient for provider-native list storage.
- The implementation plan therefore proposes:
  - provider-native artist/release and artist/track credit tables
  - generic catalog list and list-item tables for all artist-facing collections
  - explicit release segmentation confidence
