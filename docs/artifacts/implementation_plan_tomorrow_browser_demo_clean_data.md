# Implementation Plan: Tomorrow Browser Demo With Clean Data

Status: prepared on `2026-03-19` for execution on `2026-03-20`.

## Goal

By the end of tomorrow, you should be able to:

1. start the project in an isolated demo environment
2. open the browser on `/ui`
3. search artists from a clean state
4. show stable, bounded demo behavior without relying on leftover cache or stale local data

## Scope

This plan targets `MVP/demo readiness`, not production rollout.

Primary outcome:

- browser demo for artist search from a clean environment

Secondary outcome:

- optionally open the artist overview for the known probe artists

Stretch outcome:

- optionally demonstrate sync and post-sync artist enrichment if the worker path is stable tomorrow

## Assumptions

- demo will run locally on your machine, not in a cloud environment
- Docker, PostgreSQL, Redis, and localhost TCP access are available on the demo machine
- real provider tokens can be read from `.env` without printing them
- "clean data" means:
  - isolated PostgreSQL database
  - isolated Redis DB/instance
  - no leftover `search_cache`
  - no leftover `sync_jobs`
  - migrations applied from scratch
- minimum certified live query set for tomorrow is:
  - `Krovostok`
  - `Motorama`

## What Is Missing Right Now

1. there is no single reset/start workflow for a clean demo run
2. there is no tracked demo runbook for `browser + clean DB + live search`
3. current WIP is test-green, but the exact dirty worktree has not yet been re-certified end-to-end
4. current strongest live evidence is still a narrow dated artist-sync snapshot, not a certified clean-search browser flow
5. test-only seed helpers exist, but there is no runtime/demo utility that resets and certifies a clean demo state

## Tomorrow Success Criteria

Tomorrow is successful only if all of the following are true:

1. one command or one short command sequence resets the demo environment to a clean state
2. one command or one short command sequence starts API runtime for browser use
3. `/health` returns `200` in the demo environment
4. `/ui` opens in the browser and accepts artist search input
5. from a clean state, `Krovostok` and `Motorama` produce a stable, documented search result path
6. the exact commands and observed results are written to a new dated walkthrough artifact

## Non-Goals For Tomorrow

- production deployment
- general proof for arbitrary artist queries
- broad provider-quality guarantees
- full productization of sync/worker for all entity types
- redesign of the UI

## Recommended Execution Order

Implement tomorrow in four milestones. Each milestone stays within one primary subsystem.

## Milestone 1: Demo Runtime Reset And Bootstrap

Subsystem: `scripts`

### Goal

Create a deterministic clean-start path for the demo environment.

### Deliverables

- new reset/bootstrap script for isolated demo PostgreSQL + Redis
- optional env helper for demo-specific ports/project name
- exact commands documented in a walkthrough artifact

### Recommended Files

- `scripts/reset_demo_env.sh` or `scripts/demo_reset.py`
- `scripts/run_demo_api.sh`
- optionally `scripts/run_demo_worker.sh`
- `docs/artifacts/walkthrough_browser_demo_clean_data.md`

### Required Behavior

- use a dedicated compose project name for the demo stack
- start isolated `postgres` and `redis`
- wait for readiness
- recreate clean database state
- flush Redis state used for rate limits, jobs, and caches
- run `alembic upgrade head`
- print only safe operational information
- never print provider tokens

### Acceptance

- after reset, `artists`, `search_cache`, and `sync_jobs` are empty or at known clean counts
- after startup, `GET /health` returns `200`
- the demo runtime is independent from stale local dev data

### Notes

- use PostgreSQL + Redis, not ad hoc SQLite, for the demo target
- this removes ambiguity around "clean data" and aligns the browser demo with the staging-like runtime shape

## Milestone 2: Live Search Certification For The Demo Query Set

Subsystem: `search`

### Goal

Certify a clean-state browser/API search flow for a narrow query set that is actually presentation-safe tomorrow.

### Deliverables

- exact clean-state verification for:
  - `/search?q=Krovostok&kind=artist&limit=5`
  - `/search?q=Motorama&kind=artist&limit=5`
- if needed, small search fixes limited to deterministic artist ranking or live query handling
- a new dated verification artifact for tomorrow's run

### Recommended Files

- `app/services/search_service.py` only if live evidence shows a search-only defect
- `tests/api/test_search.py` for any narrow regression needed
- `docs/artifacts/walkthrough_browser_demo_clean_data.md`

### Required Behavior

- from a clean DB and clean cache state, both probe queries return `200`
- result ordering is stable enough for demo use
- when a canonical artist is created, the UI primary CTA remains obvious
- any remaining ambiguity stays visible rather than being hidden behind a false redirect

### Acceptance

- the exact top artist result for both queries is written into the walkthrough
- the cold path and warm path are both described
- if one query is still not stable, either:
  - fix it within the search subsystem, or
  - remove it from the certified demo query set

### Notes

- do not widen the certified query set tomorrow unless you also capture exact evidence
- tomorrow's safe claim can stay narrow and still be presentation-usable

## Milestone 3: Browser Demo Runbook

Subsystem: `docs/artifacts`

### Goal

Make tomorrow's browser demo executable by following a short runbook, not memory.

### Deliverables

- a concise browser demo runbook
- copy-pasteable start/reset commands
- the certified query list
- expected outcomes and fallback behavior

### Recommended Files

- `docs/artifacts/browser_demo_clean_data_runbook.md`
- `README.md` only if a short pointer is needed

### Required Content

- how to reset the environment
- how to start API
- whether worker is required for the demo path
- what browser URL to open
- what two queries are certified
- what success looks like
- what degraded behavior is acceptable
- what you must not claim during the presentation

### Acceptance

- another engineer should be able to run the demo from the runbook without asking clarifying questions

## Milestone 4: Optional Artist Overview And Sync Certification

Subsystem: `worker/sync`

### Goal

Only if Milestones 1-3 are already green, decide whether to certify the richer artist case for the presentation.

### Deliverables

- optional worker startup path
- optional verified flow:
  - search artist
  - open artist overview
  - enqueue sync
  - inspect `/ui/jobs/{job_id}`
  - confirm post-sync artist enrichment

### Recommended Files

- `scripts/run_demo_worker.sh`
- `docs/artifacts/walkthrough_browser_demo_clean_data.md`
- possibly `docs/artifacts/production_like_verification.md` append-only note if the exact current branch is re-certified

### Acceptance

- only claim this path in the presentation if tomorrow's exact branch reproduces it cleanly
- if the worker path is flaky, cut it from the live presentation and keep the demo search-only

## Concrete Tomorrow Schedule

### 10:00-11:30

Milestone 1:

- freeze the branch state you want to demo
- create reset/bootstrap scripts
- verify clean PostgreSQL + Redis startup
- verify `GET /health`

### 11:30-13:00

Milestone 2:

- run clean-state search probes for `Krovostok` and `Motorama`
- capture cold and warm results
- fix only search-subsystem issues if evidence shows a real defect
- add the narrow regression tests if code changed

### 14:00-15:00

Milestone 3:

- write the browser demo runbook
- reduce the operator steps to the minimum
- record the exact browser URL and certified query set

### 15:00-16:30

Decision point:

- if search-only demo is already clean and stable, stop widening scope
- only then attempt Milestone 4 for artist overview + sync

### 16:30-17:30

Final certification:

- reset from scratch one more time
- re-run the exact demo flow once without improvisation
- update the walkthrough artifact with exact commands and outcomes

## Recommended Demo Scope For Tomorrow

### Must-Have

- browser `/ui`
- clean reset
- `Krovostok` search
- `Motorama` search
- stable top result / primary CTA behavior

### Nice-To-Have

- open `/ui/artists/{artist_id}` from the primary CTA for the certified queries

### Stretch

- worker-backed sync and post-sync Yandex enrichment

## Risks And Pre-Decisions

### Risk 1: Live search is still unstable for one probe query

Decision:

- keep the certified query set narrow
- drop any unstable query from the live presentation rather than bluffing broader readiness

### Risk 2: Worker path is operationally flaky

Decision:

- keep tomorrow's presentation search-first
- do not rely on live sync unless it reproduces cleanly on the exact branch

### Risk 3: Dirty worktree hides cause/effect

Decision:

- freeze the branch before runtime certification
- do not certify the browser demo on a moving target

### Risk 4: "Clean data" is interpreted differently by different people

Decision:

- define it operationally as isolated Postgres + isolated Redis + migrated schema + empty cache/jobs
- document that definition in the runbook and walkthrough

## Exact Outcome We Want Tomorrow Evening

You can say and demonstrate the following without stretching:

- "Я поднимаю чистое demo-окружение."
- "Открываю браузер на `/ui`."
- "На чистой базе прогоняю `Krovostok` и `Motorama`."
- "Для этих запросов у нас есть зафиксированный и воспроизводимый demo flow."

If Milestone 4 also goes green, you may extend that to:

- "Из поиска мы открываем overview артиста и можем показать enrichment/sync path."

If Milestone 4 does not go green, do not widen the live story beyond search + overview.
