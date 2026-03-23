# Walkthrough: Frontend Artist MVP Phase 2 Milestone 5 Deterministic Artist Search For Live Queries

Status: completed on `2026-03-19` with targeted automated coverage green; conditional live probe skipped.

## Goal

Make live `artist` search more deterministic for `Krovostok` and `Motorama` by changing backend search ranking and selection only, so the intended canonical artist becomes the top backend result without widening scope into sync, detail refresh, Yandex catalog ingest, or frontend runtime changes.

## Scope

- `app/services/search_service.py`
- `tests/api/test_search.py`
- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`

Out of scope:

- `app/web/*`
- sync, worker, queue, or provider runtime code
- Yandex subsystem changes
- artist detail pages
- shared docs and historical milestone artifacts
- unrelated dirty files

## Source Of Truth

- `docs/project_brief.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_youtube_detail_refresh_unblock.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_docs_alignment_after_youtube_detail_refresh_unblock.md`

## Dirty-Worktree Note

Before this milestone started, the worktree already contained unrelated modified and untracked files outside the search subsystem, including provider, Yandex, worker, web UI, shared docs, and non-search test changes. This milestone must edit only the search service, the targeted search API tests, and these new milestone artifacts.

## Milestone Log

### Milestone 0: Artifact Bootstrap

Changed files:

- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`

Commands run:

- `git status --short`
- `ls docs/artifacts | rg "milestone_5_deterministic_artist_search_for_live_queries|milestone_5"`

Tests run:

- none

Notes:

- created the new Implementation Plan artifact first, per project instructions
- created the new Walkthrough artifact before runtime code edits
- historical milestone artifacts remain append-only and untouched

### Milestone 1: Query-Aware Artist Ranking In Search Service

Changed files:

- `app/services/search_service.py`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`

Commands run:

- `sed -n '1,460p' app/services/search_service.py`

Tests run:

- none

Notes:

- kept provider fan-out, matching decisions, link persistence, and non-artist search behavior unchanged
- added artist-only query-aware ranking metadata under `features_json.search_rank_*`
- preserved the raw matching score as `search_rank_matching_score`
- bumped cache keys from `search:v1` to `search:v2` to avoid serving pre-rerank artist ordering
- added deterministic tiebreak sorting using primary label, canonical id, and provider ids

### Milestone 2: Targeted Automated Coverage

Changed files:

- `tests/api/test_search.py`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`

Commands run:

- `.venv/bin/python -m pytest -q tests/api/test_search.py`
- `.venv/bin/ruff check app/services/search_service.py tests/api/test_search.py`

Tests run:

- `.venv/bin/python -m pytest -q tests/api/test_search.py`
  - `15 passed in 0.85s`
- `.venv/bin/ruff check app/services/search_service.py tests/api/test_search.py`
  - `All checks passed!`

Notes:

- added query-aware ranking regressions for both accepted live-query shapes:
  - `Krovostok`
  - `Motorama`
- verified that the exact canonical artist now outranks a noisier live/archive result even when the noisier result keeps the higher raw matching score
- added a cache regression proving a seeded `search:v1:artist:...` row no longer masks the new ranking logic
- added a warm-cache determinism regression proving miss and fresh-cache responses keep the same top canonical artist and displayed score
- kept existing provider-failure, stale-cache, no-provider, and rate-limit tests intact

### Milestone 3: Conditional Live Verification

Changed files:

- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`

Commands run:

- `curl -sS -i http://127.0.0.1:8000/health`
- `curl -sS -i http://127.0.0.1:8001/health`
- `git diff -- app/services/search_service.py tests/api/test_search.py docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`
- `git status --short app/services/search_service.py tests/api/test_search.py docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`

Tests run:

- none beyond the green targeted automated coverage above

Notes:

- conditional live probe was attempted by first checking for an already-running local API
- both `127.0.0.1:8000` and `127.0.0.1:8001` returned connection failures
- a new host-run API session was not started because this sandbox does not provide a trustworthy live-provider signal for outbound search, so forcing a local `/search` probe here would not add reliable evidence
- milestone acceptance is therefore supported by deterministic targeted tests and code-level cache/version verification, not by a live provider probe

## Final Outcome

- backend search now applies query-aware artist ranking only for `kind=artist`
- exact canonical artist results for the accepted query shapes are now stable top results in targeted automated coverage
- explainability did not regress:
  - existing matching features remain present
  - raw matching score is still exposed as `search_rank_matching_score`
- the ambiguous-over-false-match policy remains unchanged because matching decisions were not rewritten
- historical milestone artifacts were not rewritten; newer state is captured only in these new milestone artifacts
