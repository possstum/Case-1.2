# Remaining Steps: Frontend Artist MVP

Status: captured on `2026-03-19`.

## Remaining Work

1. Make artist search deterministic for live queries.
   Today the frontend flow works once the query resolves to an existing canonical artist. For a stronger MVP, the top artist hit should either auto-promote more clearly in the UI or redirect more directly into the artist overview flow.

2. Add provider-native Yandex release sections to the artist page.
   The current page shows canonical linked releases and clearly marks Yandex gaps. The next useful step is to expose Yandex catalog lists such as direct albums and adjacent release groups from `platform_catalog_lists`.

3. Expand the missing-on-Yandex view from linked canonical rows to a dedicated artist-level read model.
   Right now `Missing on Yandex` is derived from canonical release links. A stronger MVP should support a backend query specifically optimized for artist catalog comparison and missing-Yandex browsing.

4. Validate the whole frontend flow with live tokens and worker refresh.
   The current frontend MVP is still limited by the existing production-like verification gap and by the unfinished YouTube detail refresh path.

5. After live verification, tighten the frontend copy and docs.
   Only after the live flow is confirmed should the docs make stronger claims about artist search, release availability, and missing-on-Yandex readiness.
