# Implementation Plan: Frontend Artist MVP Phase 2 Milestone 5 Deterministic Artist Search For Live Queries

Status: approved and ready for implementation on `2026-03-19`.

## Summary

- Goal: make live `artist` searches deterministic for the accepted probe queries `Krovostok` and `Motorama`, so the intended canonical artist becomes the backend top result and the existing UI primary CTA follows it, without touching worker, sync, Yandex, artist detail, or frontend runtime code.
- Source of truth:
  - `docs/project_brief.md`
  - `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_youtube_detail_refresh_unblock.md`
  - `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_docs_alignment_after_youtube_detail_refresh_unblock.md`
- Scope: `app/services/search_service.py`, `tests/api/test_search.py`, and milestone artifacts only.
- Out of scope: `app/web/*`, `app/services/sync_service.py`, worker/queue files, provider clients, Yandex catalog ingest, artist detail pages, shared docs, and unrelated dirty files.

## Grounded Facts

- Search results are currently sorted by `decision`, raw `score`, and `kind`; there is no query-aware artist reranking in the search service.
- The web primary artist CTA is selected from backend results using `decision` then `score`, so API reordering alone is not enough if `score` stays match-only.
- Search cache keys are still `search:v1:...`; without a cache revision, existing live responses can continue serving pre-rerank ordering.
- The worktree already contains unrelated dirty files. This milestone must not touch them.

## Important Interface Changes

- `GET /search` response schema does not change.
- For `kind=artist` searches only, `results[].score` becomes a composite query-aware search ranking score instead of a pure cross-provider match score.
- For `kind=artist` searches only, `results[].features_json` gains explicit ranking fields and preserves the raw match score under `search_rank_matching_score`.
- Internal cache contract changes from `search:v1` to `search:v2` so old cached artist responses cannot mask the new ranking behavior.

## Dirty-Worktree Note

Observed before this milestone:

- modified unrelated files in README, providers, Yandex services, worker/queue, artist detail, web UI, shared docs, and non-search tests
- untracked historical milestone artifacts from prior work
- untracked `tests/tasks/`

This milestone may edit only:

- `app/services/search_service.py`
- `tests/api/test_search.py`
- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`

## Milestone 0: Artifact Bootstrap

Files to create first:

- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`

Requirements:

- mark this as a search-subsystem-only milestone dated `2026-03-19`
- reference the newer verified sync/docs state instead of rewriting historical milestone artifacts
- record the dirty-worktree note from `git status --short`

## Milestone 1: Query-Aware Artist Ranking In Search Service

Files to change:

- `app/services/search_service.py`

Implementation rules:

- keep provider fan-out, matching thresholds, link persistence, cache repository shape, and non-artist search behavior unchanged
- limit the new ranking behavior to requests where `context.kind == "artist"`
- preserve existing `decision` values from `MatchingService`

Implementation details:

- pass `SearchContext` into result merging so query-aware artist scoring has access to `normalized_query`
- after artist results are merged, compute query affinity against available platform labels in fixed provider order `("yandex", "youtube")`
- use the best available platform label per result for explainability and composite scoring
- compute per-result ranking inputs:
  - `query_exact_match`: `1.0` when platform `match_norm == normalized_query`, else `0.0`
  - `query_prefix_match`: `1.0` when platform `match_norm` starts with `normalized_query` or the reverse, else `0.0`
  - `query_token_overlap`: max `token_jaccard(norm_tokens(normalized_query), norm_tokens(platform.match_norm))`
  - `query_sequence_similarity`: max `sequence_similarity(normalized_query, platform.match_norm)`
  - `platform_coverage`: `available_platforms / 2`
  - `canonical_bonus`: `1.0` when `canonical_id is not None`, else `0.0`
  - `matching_score`: the unchanged raw `match_result.score`
- compute the artist search ranking score with:

```text
query_affinity = rounded(
  0.55 * query_exact_match
  + 0.20 * query_prefix_match
  + 0.15 * query_token_overlap
  + 0.10 * query_sequence_similarity
)

artist_search_score = rounded(
  0.60 * query_affinity
  + 0.25 * matching_score
  + 0.10 * platform_coverage
  + 0.05 * canonical_bonus
)
```

- write `artist_search_score` into `SearchResultItemPayload.score` for `kind=artist` requests only
- keep raw matching explainability intact by merging these fields into `features_json` after link persistence:
  - `search_rank_version: "artist_query_v1"`
  - `search_rank_query_match_norm`
  - `search_rank_best_platform`
  - `search_rank_query_exact_match`
  - `search_rank_query_prefix_match`
  - `search_rank_query_token_overlap`
  - `search_rank_query_sequence_similarity`
  - `search_rank_platform_coverage`
  - `search_rank_matching_score`
  - `search_rank_score`
- keep all existing matching keys already present in `features_json`; add to them, do not replace them
- change the cache key builder to `search:v2:{kind or 'all'}:{limit}:{normalized_query}`
- add stable sort tiebreaks after `decision` and `-score`:
  - primary label `casefold()`
  - `canonical_id or 0`
  - youtube `provider_id` or `""`
  - yandex `provider_id` or `""`

## Milestone 2: Targeted Automated Coverage

Files to change:

- `tests/api/test_search.py`

Tests to add or update:

- add a parametrized regression for the accepted live-query shapes `Krovostok` and `Motorama`
- in each case, return two canonical artist candidates from stub providers:
  - the desired canonical result with stronger query affinity but lower raw matching score
  - a distractor canonical result with weaker query affinity but higher raw matching score
- assert that `results[0]` is the desired canonical artist for both query shapes
- assert that `results[0].score > results[1].score` while `results[0].features_json["search_rank_matching_score"] < results[1].features_json["search_rank_matching_score"]`
- assert that existing matching explainability keys remain present alongside the new `search_rank_*` keys
- add a cache regression where an old `search:v1:artist:...` row is seeded and the request still performs a live merge, returns `cache.status == "miss"`, and writes a `search:v2:artist:...` row
- add a warm-cache determinism regression for one accepted query:
  - first request is a miss
  - second identical request is fresh cache
  - top canonical artist id, top provider ids, and displayed `score` stay identical across both responses
- keep all non-artist, provider-failure, stale-cache, and rate-limit tests unchanged

Planned commands:

- `.venv/bin/python -m pytest -q tests/api/test_search.py`
- `.venv/bin/ruff check app/services/search_service.py tests/api/test_search.py`

## Milestone 3: Conditional Live Verification And Walkthrough

Files to update:

- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`

Verification rules:

- run live verification only after Milestone 2 is green
- keep it read-only and limited to `/search`
- do not touch sync, worker, detail refresh, Yandex catalog ingest, or web runtime code

Conditional live probe flow:

- if a local API process with real provider tokens is already available, use it
- otherwise, if the environment allows a short host-run API session, start only the API and probe `/search`
- probe both accepted queries:
  - `GET /search?q=Krovostok&kind=artist&limit=5`
  - `GET /search?q=Motorama&kind=artist&limit=5`
- for each query, issue the request twice and compare cold and warm results

Acceptance:

- `results[0]` is `kind="artist"`
- `results[0].canonical_id` is not `null`
- `results[0].features_json["search_rank_version"] == "artist_query_v1"`
- the same top canonical id and provider ids are returned on the repeat request
- the repeat request uses cached data without changing the primary result

If live probing is not possible:

- record the exact blocker in the walkthrough
- mark the milestone as validated by targeted automated coverage only
- do not expand scope into provider client, worker, or UI changes

## Failure Rules

- any required fix outside `app/services/search_service.py`, `tests/api/test_search.py`, or the two new artifact files stops the milestone
- any need to change worker, sync, Yandex, provider client, artist detail, or web UI runtime code stops the milestone
- if the accepted queries can only be stabilized by rewriting `decision` semantics rather than by query-aware artist scoring inside the existing decision bucket, stop and record a new blocker instead of weakening the ambiguous-over-false-match rule
- if the cache revision causes broader search regressions outside `kind=artist`, stop and record the regression rather than widening scope

## Test Cases And Scenarios

- exact canonical artist should beat a noisier canonical artist when the noisier result only wins on raw cross-provider match score
- the same behavior must hold for both `Krovostok` and `Motorama`
- existing matching explainability must remain visible after ranking metadata is added
- old `search:v1` cached artist responses must not mask the new ranking behavior
- warm-cache replay must preserve the same top canonical result as the cold miss
- non-artist search behavior and all existing verified sync/docs claims must remain unchanged

## Assumptions And Defaults

- accepted live-query scope is exactly `Krovostok` and `Motorama`
- live verification is conditional, not mandatory
- `results[].score` becoming a composite artist search score is acceptable because the raw matching score remains explicitly available in `features_json`
- `app/web/render.py` remains untouched; the existing UI primary CTA should follow the backend change because it already keys off `decision` and `score`
- historical milestone artifacts remain append-only
