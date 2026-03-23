# Implementation Plan: Frontend Artist MVP Phase 2 Milestone 4 Docs Alignment After YouTube Detail Refresh Unblock

Status: approved and ready for implementation on `2026-03-19`.

## Summary

- Goal: align shared docs with the already-verified production-like result from `2026-03-19` after the YouTube detail refresh unblock.
- Scope: create this implementation plan artifact, update `README.md`, update `docs/project_brief.md`, update `docs/artifacts/production_like_verification.md`, and create a docs-only walkthrough artifact for this follow-up.
- Source of truth for the newer verified state: `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_youtube_detail_refresh_unblock.md`.
- Out of scope: runtime code, tests, Yandex subsystem changes, frontend copy changes, and unrelated files.

## Public APIs And Interfaces

- No API routes, schemas, DB models, env vars, or runtime types change.
- Only documentation claims and milestone artifact inventory change.

## Canonical Verified Wording

- Always use the absolute date `2026-03-19`.
- The newer verified production-like result must be described consistently as:
  - `/jobs/{job_id}` reached `finished`
  - both providers had `status="updated"`
  - YouTube had `mode="entity_refresh"`
  - Yandex had `mode="catalog_ingest"`
  - `partial=false`
  - post-sync `/artists/{id}` still had non-empty `yandex_catalog_sections`
  - post-sync `/ui/artists/{id}` still showed `Yandex native catalog`
- The older `partial=true` Yandex-only result in `docs/artifacts/production_like_verification.md` must remain preserved as historical evidence and be explicitly labeled as the older state.

## Milestone 0: Artifact Bootstrap

Files to create:

- `docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2_milestone_4_docs_alignment_after_youtube_detail_refresh_unblock.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_docs_alignment_after_youtube_detail_refresh_unblock.md`

Requirements:

- create the implementation plan artifact first
- create the walkthrough artifact in the same milestone
- each walkthrough milestone section must include `Changed files`, `Commands run`, `Tests run`, and `Notes`

## Milestone 1: Shared Docs Alignment

Files to change:

- `README.md`
- `docs/project_brief.md`

Changes:

- update the README top-level verified-baseline date from `2026-03-16` to `2026-03-19`
- remove claims that YouTube `get_*()` remains stubbed or unverified for the verified artist-sync snapshot
- add one narrow statement that a production-like artist sync path with real tokens is verified on `2026-03-19`
- keep broader live-provider search and readiness claims partial
- align `SyncService`, `YandexCatalogIngestionService`, jobs-flow, and live-refresh wording in `docs/project_brief.md` with the newer verified state
- remove `YouTubeMusicClient.get_*()` from the brief's `Stub / Placeholder` section

## Milestone 2: Verification Artifact Alignment

Files to change:

- `docs/artifacts/production_like_verification.md`
- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_docs_alignment_after_youtube_detail_refresh_unblock.md`

Changes:

- edit the current worktree version of `docs/artifacts/production_like_verification.md` in place
- prepend a short `Newer verified state on 2026-03-19` section that points to the YouTube detail refresh unblock walkthrough and lists the canonical `partial=false` bullets
- add an explicit note that the older `partial=true` payload below remains valid historical evidence for the Yandex 403 fix milestone and is intentionally not rewritten
- complete the new walkthrough artifact with the docs-only milestone log and final verdict

## Validation

- use `rg` to confirm `README.md` and `docs/project_brief.md` no longer claim YouTube `get_*()` is stubbed or unimplemented
- use `rg` to confirm `2026-03-19`, `partial=false`, `entity_refresh`, `catalog_ingest`, and `Yandex native catalog` appear in the aligned docs and artifacts
- use `git diff --` to confirm only the planned target files changed
- no automated test suites are required; record `none (docs-only)` in the walkthrough

## Assumptions And Defaults

- `docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_4_youtube_detail_refresh_unblock.md` remains read-only in this follow-up
- the untracked implementation-plan artifact for the YouTube unblock remains read-only in this follow-up
- shared docs will make a narrow claim about one verified production-like artist sync result, not a blanket production-readiness claim for arbitrary live-provider behavior
- chronology must remain explicit and older verification history must not be silently rewritten
