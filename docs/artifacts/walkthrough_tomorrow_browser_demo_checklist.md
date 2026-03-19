# Walkthrough: Tomorrow Browser Demo Checklist

Status: completed on `2026-03-19`.

## Goal

Turn the higher-level tomorrow demo plan into a strict execution checklist for `2026-03-20`.

## Scope

- `docs/artifacts/tomorrow_browser_demo_checklist.md`
- `docs/artifacts/walkthrough_tomorrow_browser_demo_checklist.md`

Out of scope:

- `app/*`
- `tests/*`
- scripts implementation
- runtime verification itself

## Milestone Log

### Milestone 1: Checklist Artifact

Changed files:

- `docs/artifacts/tomorrow_browser_demo_checklist.md`
- `docs/artifacts/walkthrough_tomorrow_browser_demo_checklist.md`

Commands run:

- `sed -n '1,320p' docs/artifacts/implementation_plan_tomorrow_browser_demo_clean_data.md`
- `sed -n '1,220p' docs/artifacts/walkthrough_tomorrow_browser_demo_clean_data_planning.md`

Tests run:

- none

Checklist design decisions:

- made the demo explicitly `search-first`
- treated `Krovostok` and `Motorama` as the only certified live query set for tomorrow unless re-verified
- treated worker/sync as optional stretch scope
- defined `clean data` operationally as isolated PostgreSQL + isolated Redis + migrated schema + empty cache/jobs
- added hard go/no-go gates so the presentation cannot silently expand beyond verified evidence

## Final Outcome

- created a strict hour-by-hour checklist for tomorrow
- kept the milestone limited to `docs/artifacts`
- did not modify application code or runtime behavior
