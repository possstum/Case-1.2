# Walkthrough: Full Track Search Results

## Scope

- Remove the current low cap that makes track search results look artificially incomplete.
- Preserve existing API contracts and matching logic.
- Deliver full track search results by default for track searches, while keeping artist/release behavior compact.

## Milestones

### Milestone 1

- Status: completed
- Files:
  - `docs/artifacts/implementation_plan_search_full_track_results.md`
  - `docs/artifacts/walkthrough_search_full_track_results.md`
- Commands:
  - `sed -n '1,220p' docs/project_brief.md`
  - `rg --files docs/artifacts`
- Tests: none

### Milestone 2

- Status: completed
- Files:
  - `app/providers/base.py`
  - `app/providers/youtube_music/client.py`
  - `app/providers/yandex_music/client.py`
  - `app/services/search_service.py`
  - `app/api/deps.py`
  - `app/core/config.py`
  - `.env`
  - `app/web/presenters.py`
- Commands:
  - `sed -n '1,260p' app/services/search_service.py`
  - `sed -n '1,260p' app/providers/youtube_music/client.py`
  - `sed -n '1,300p' app/providers/yandex_music/client.py`
  - `rg -n "SEARCH_DEFAULT_LIMIT|SEARCH_MAX_LIMIT" .env README.md docs app -g '!**/.venv/**'`
- Tests: covered in Milestone 3

### Milestone 2 Outcome

- `limit=None` is now interpreted as full provider result set for `kind=track`.
- Track searches paginate until provider exhaustion instead of stopping at the old local cap.
- `/ui?tab=all` no longer slices tracks to `[:3]`; the track section now renders all found tracks for the query.
- Explicit limits are still supported; `SEARCH_MAX_LIMIT` was raised from `10` to `250` for manual/API usage.

### Milestone 3

- Status: completed
- Files:
  - `tests/providers/test_provider_contracts.py`
  - `tests/providers/test_provider_clients.py`
  - `tests/test_support.py`
  - `tests/services/test_sync_service.py`
  - `tests/web/test_presenters.py`
  - `tests/api/test_web_ui.py`
  - `tests/api/test_search.py`
  - `docs/artifacts/walkthrough_search_full_track_results.md`
- Commands:
  - `.venv/bin/ruff check app tests docs/artifacts/implementation_plan_search_full_track_results.md docs/artifacts/walkthrough_search_full_track_results.md`
  - `.venv/bin/pytest -q tests/providers/test_provider_clients.py tests/web/test_presenters.py tests/api/test_web_ui.py tests/api/test_search.py`
  - `.venv/bin/pytest -q`
- Tests:
  - targeted: `64 passed`
  - full suite: `115 passed`

## Notes

- Exact semantics after implementation:
  - `/search?kind=track` without `limit` now means full track result set that the current provider adapters can page through.
  - `/search?kind=artist` and `/search?kind=release` without `limit` still use the compact default.
  - `/ui?tab=track` without `limit` requests full track results.
  - `/ui?tab=all` still keeps artists/releases compact, but no longer truncates tracks to three cards.
- Remaining external limits:
  - YouTube search is still bounded by what the YouTube API exposes through paginated `search.list`.
  - Yandex search is still bounded by what the public search endpoint returns across paginated pages.
  - The app now stops being the bottleneck for track searches; provider-side coverage remains the outer bound.
