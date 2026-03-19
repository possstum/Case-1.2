# Implementation Plan: Frontend Artist MVP Phase 2

Status: draft on `2026-03-19`.

## Summary

- Goal: close the remaining gap from the current artist overview MVP to a stronger user-facing artist flow.
- Source of truth: `docs/project_brief.md` and `docs/artifacts/frontend_artist_mvp_remaining_steps.md`.
- Constraint: one subsystem per milestone; keep diffs compact and explainable.

## Milestones

### Milestone 1: Deterministic Artist Entry Flow

Subsystem: web UI search flow

- keep `/search` and provider fan-out unchanged for now
- make `/ui` steer artist queries into the artist overview flow more explicitly
- prefer a deterministic primary CTA over ambiguous mixed-result browsing

Acceptance:

- an artist search on `/ui` exposes one obvious path into `/ui/artists/{id}`
- ambiguous results stay visible instead of being hidden behind a false redirect

### Milestone 2: Provider-Native Yandex Artist Sections

Subsystem: artist detail read model

- extend artist detail loading to include Yandex `platform_catalog_lists` for the linked Yandex artist
- expose at least direct albums and nearby Yandex artist/release groupings as explicit sections
- keep canonical linked releases and provider-native Yandex lists visually separated

Acceptance:

- `/artists/{id}` returns enough data to render Yandex-native sections without guessing from canonical links alone
- `/ui/artists/{id}` shows direct Yandex albums and adjacent Yandex groups as separate blocks

### Milestone 3: Missing-On-Yandex Artist Read Model

Subsystem: backend comparison read model

- stop deriving the whole missing-Yandex view only from current canonical release links
- add a dedicated artist-level comparison query optimized for browsing catalog gaps
- keep the matching policy conservative and prefer ambiguous over false match

Acceptance:

- artist detail can render a missing-on-Yandex section backed by a dedicated read model
- the section remains explainable about what is linked, what is provider-native, and what is still unresolved

### Milestone 4: Production-Like Verification

Subsystem: runtime verification

- run artist search, artist detail, sync enqueue, worker execution, and Yandex catalog refresh with real tokens
- verify behavior against PostgreSQL + Redis + worker, not only SQLite request tests
- document exact verified claims and leave unverified claims out

Acceptance:

- production-like verification artifact exists with exact commands, environment, and observed outcomes
- frontend/docs claims only reflect verified runtime behavior

### Milestone 5: Copy And Docs Tightening

Subsystem: frontend copy and docs

- update hero/search/artist copy only after live verification
- align docs and artifacts with the verified behavior

Acceptance:

- no stronger UX or provider claims remain than those proven in Milestone 4

## What I Need From The User

1. Approve which milestone to do first.
   Recommended: Milestone 1, then Milestone 2.

2. Confirm the desired deterministic search behavior.
   Recommended default: keep the result list, but promote the best canonical artist hit with one primary CTA instead of auto-redirecting immediately.

3. For Milestone 4, provide a live verification environment.
   Needed: real provider tokens available via env, reachable PostgreSQL + Redis, and a worker process we can run or inspect.

4. Confirm whether live verification may use the current `.env` values if they are already populated locally.

## Notes

- `platform_catalog_lists` already exists in the schema, so Milestone 2 looks feasible without a new storage subsystem.
- The current `/ui` route still behaves as a generic search page; deterministic artist entry can likely be improved without touching provider search semantics first.
- `gh` is unavailable here, so PR creation remains outside this plan.
