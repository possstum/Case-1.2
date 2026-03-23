# Implementation Plan: Full Track Search Results

## Summary

- Goal: stop truncating track search results to the current small UI/service defaults so the product can show the full provider result set for track searches.
- Scope: search UX and search service limit handling only. No provider auth, no ranking rewrite, no schema changes.
- Constraint: keep existing `/search` contract shape stable and avoid a broad backend refactor.

## Grounded Facts

- The `Все` tab currently renders track previews only: [app/web/presenters.py](/Users/possstum/Documents/WorkID2/app/web/presenters.py) slices tracks with `[:3]`.
- The backend search service normalizes `limit` against defaults/max values: [app/services/search_service.py](/Users/possstum/Documents/WorkID2/app/services/search_service.py).
- Local config still caps search to `SEARCH_DEFAULT_LIMIT=5` and `SEARCH_MAX_LIMIT=10` in [.env](/Users/possstum/Documents/WorkID2/.env).
- The merged search result list is not additionally truncated after merge in `SearchService`; the current bottleneck is the normalized per-provider request limit plus the UI preview slice.

## Milestones

1. Milestone 1: search limit analysis and artifact update.  
   Subsystem: docs only.  
   Files: `docs/artifacts/implementation_plan_search_full_track_results.md`, `docs/artifacts/walkthrough_search_full_track_results.md`.  
   Changes: record the current caps and the intended minimal fix.  
   Validation: `sed -n '1,220p'` on both artifacts.  
   Tests: none.

2. Milestone 2: remove practical truncation for track search flows.  
   Subsystem: search service and web presenter.  
   Files: `app/core/config.py`, `app/services/search_service.py`, `app/web/presenters.py`, `.env` if needed.  
   Changes: stop limiting visible track results to preview-only behavior where that harms product meaning; allow search requests to use a much larger effective limit; keep `Все` as a preview surface but make the dedicated `Треки` tab represent the full provider set.  
   Validation: `ruff check` on touched files.  
   Tests: service/presenter tests for limit normalization and full track tab rendering.

3. Milestone 3: regression coverage and walkthrough.  
   Subsystem: tests/docs.  
   Files: `tests/web/test_presenters.py`, `tests/api/test_web_ui.py`, `docs/artifacts/walkthrough_search_full_track_results.md`.  
   Changes: encode the new semantics in rendering and response tests; document remaining provider-side limits and out-of-scope items.  
   Validation: target `pytest` on touched suites, then full `pytest -q` if clean.  
   Tests: explicit assertions, no snapshot introduction.

## Intended Outcome

- `tab=track` should show the full set of track results returned by providers for the effective request limit, not just 5 or 10.
- `tab=all` may remain a preview surface, but it must clearly lead into `Треки`.
- If providers themselves cap search results, that limitation must be documented in the walkthrough rather than hidden behind a smaller local cap.
