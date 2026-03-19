# Checklist: Tomorrow Browser Demo With Clean Data

Status: prepared on `2026-03-19` for execution on `2026-03-20`.

## Rule Zero

Tomorrow's presentation target is:

- clean environment
- browser `/ui`
- live artist search
- narrow, reproducible demo story

Tomorrow's presentation target is **not**:

- proving general provider quality
- proving all sync paths
- improvising new queries during the demo

## Certified Demo Scope

### Must Show

- clean reset of the demo environment
- `GET /health`
- browser open on `/ui`
- `Krovostok` search
- `Motorama` search
- stable top result or obvious primary CTA

### Show Only If Green Tomorrow

- open artist overview from search
- known artist detail page from the CTA

### Cut Unless Fully Re-Verified Tomorrow

- live sync
- worker-backed refresh
- post-sync Yandex enrichment

## Current State On `2026-03-19`

- clean reset path exists: `./scripts/reset_demo_env.sh`
- clean demo API start path exists: `./scripts/run_demo_api.sh`
- `Motorama` is certified on cold and warm `/search` and `/ui`
- `Krovostok` is certified on cold and warm `/search` and `/ui`
- sync and worker-backed refresh remain cut from the first-user MVP story
- `Krovostok` currently renders a primary CTA label `Krovostok - Topic`, so the presentation must keep ambiguity visible instead of overselling perfect top-label quality

## 10:00-10:30 Freeze The Demo Target

Checklist:

- [ ] stop changing unrelated code
- [ ] decide which exact branch/worktree state is the demo target
- [ ] record `git status --short`
- [ ] record `git diff --stat`
- [ ] do not certify a moving target

Go/No-Go:

- go only if you can point to one exact worktree state
- if the tree is still moving, freeze first and postpone wider runtime claims

## 10:30-11:30 Build Clean Reset Flow

Checklist:

- [ ] create one reset/bootstrap path for demo infra
- [ ] use isolated PostgreSQL
- [ ] use isolated Redis
- [ ] use a dedicated compose project name
- [ ] wait for both services to become healthy
- [ ] recreate the DB from scratch
- [ ] flush Redis keys for rate limits, jobs, and cache state
- [ ] run `alembic upgrade head`
- [ ] verify the database is clean
- [ ] verify `search_cache` is empty
- [ ] verify `sync_jobs` is empty

Definition Of Clean Data:

- isolated PostgreSQL database
- isolated Redis instance or DB
- migrated schema at `head`
- no stale `search_cache`
- no stale `sync_jobs`

Go/No-Go:

- go only if `/health` can later run against this clean environment
- if reset is not one short command sequence, keep working here and do not widen scope

## 11:30-12:00 Bring Up The API

Checklist:

- [ ] start API against the clean demo environment
- [ ] confirm provider tokens are loaded safely from env
- [ ] do not print tokens
- [ ] verify `GET /health` returns `200`
- [ ] verify `database.status=ok`
- [ ] verify `redis.status=ok`
- [ ] write down the exact browser URL

Go/No-Go:

- go only if API startup is deterministic
- if `/health` is not green, stop and fix runtime bootstrap before touching search

## 12:00-13:00 Certify Search Query 1: `Krovostok`

Checklist:

- [ ] hit `/search?q=Krovostok&kind=artist&limit=5` on a cold state
- [ ] capture top result
- [ ] capture whether a canonical artist was created/returned
- [ ] open `/ui?q=Krovostok&kind=artist&limit=5`
- [ ] verify the primary CTA is obvious if canonical artist exists
- [ ] repeat the same request on a warm state
- [ ] compare cold and warm behavior
- [ ] record exact observed result in walkthrough

Acceptable Outcome:

- result path is stable enough for presentation
- ambiguity stays visible if certainty is not justified

Reject Outcome:

- top result changes unpredictably between cold and warm
- primary CTA disappears or points to the wrong thing

Decision:

- if broken, fix only the search subsystem
- do not jump to worker, sync, or UI redesign

## 13:00-14:00 Certify Search Query 2: `Motorama`

Checklist:

- [ ] hit `/search?q=Motorama&kind=artist&limit=5` on a cold state
- [ ] capture top result
- [ ] open `/ui?q=Motorama&kind=artist&limit=5`
- [ ] verify the primary CTA behavior
- [ ] repeat on a warm state
- [ ] compare cold and warm behavior
- [ ] record exact observed result in walkthrough

Decision:

- if green, keep `Motorama` in the certified demo query set
- if unstable, either:
  - [ ] fix only the search subsystem and re-run
  - [ ] or drop `Motorama` from the live presentation

## 14:00-15:00 Lock The Browser Runbook

Checklist:

- [ ] write a short browser-demo runbook
- [ ] include reset command(s)
- [ ] include API start command(s)
- [ ] include browser URL
- [ ] include certified query set
- [ ] include expected outcomes
- [ ] include acceptable degraded states
- [ ] include forbidden claims during the presentation

Required Statements In The Runbook:

- "This demo is certified for the exact queries `Krovostok` and `Motorama` only."
- "This demo does not claim general live-provider readiness."
- "Worker-backed sync is out of scope unless separately re-verified on this exact branch."

## 15:00-16:00 Decide Whether To Widen Scope

Decision Gate:

- widen scope only if all previous steps are green

Checklist:

- [ ] ask whether search-only demo already satisfies the presentation need
- [ ] if yes, stop widening scope
- [ ] if no, decide whether artist overview is needed
- [ ] only if artist overview is needed, verify CTA -> `/ui/artists/{artist_id}` for the certified queries

Do Not Do At This Stage:

- do not start worker just because it exists
- do not add sync to the live story unless the search-first baseline is already certified

## 16:00-17:00 Optional Sync/Worker Path

Only run this block if everything above is green and you still need it for the presentation.

Checklist:

- [ ] start worker in the same isolated demo environment
- [ ] verify worker can consume jobs
- [ ] enqueue one known artist sync
- [ ] poll `/jobs/{job_id}`
- [ ] confirm exact terminal state
- [ ] verify post-sync artist page if and only if the flow fully succeeds

Go/No-Go:

- if anything flakes, cut sync from the presentation immediately
- revert to the certified search-only browser demo

## 17:00-18:00 Final Dress Rehearsal

Checklist:

- [ ] reset the environment from scratch one more time
- [ ] start the demo exactly as written
- [ ] open `/ui` in the browser
- [ ] run the certified query set in order
- [ ] verify the observed flow matches the runbook
- [ ] update walkthrough with exact commands and exact results

Success Condition For Tomorrow Evening:

- you can execute the full demo without improvising
- you know exactly which claims are safe
- you know exactly which optional steps to skip if they are flaky

## Hard Constraints

- do not improvise new live queries during the presentation
- do not claim broader search quality than tomorrow's evidence supports
- do not claim worker/sync success unless it is re-verified on the exact demo branch
- do not depend on stale local cache or old SQLite state

## Minimal Acceptable Outcome

If the day goes worse than planned, the minimum acceptable presentation is still:

- clean reset
- healthy API
- browser `/ui`
- one or two certified artist searches
- stable primary CTA or stable top result explanation

That is enough for a credible MVP/demo story.
