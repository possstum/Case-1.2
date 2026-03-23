# Implementation Plan: Merge-Ready PR For Yandex Catalog Ingest

Status: approved on `2026-03-19`.

## Summary

- Goal: turn the current mixed working tree into one narrow, reviewable PR for Yandex catalog ingest storage and sync wiring.
- Scope: keep Yandex search prerequisites, schema/storage, ingest service, sync wiring, targeted tests, and only the docs needed to review those changes.
- Out of scope: demo-loader work, broad baseline doc rewrites, generated metadata files, and any production-like claims.

## Milestones

### Milestone 1: Isolate PR Scope

Subsystem: repository / git hygiene

- move the current work from `main` onto a dedicated feature branch
- remove out-of-scope demo, broad-doc, and generated-file changes from the PR branch
- leave the branch with only the intended Yandex catalog ingest review unit

Acceptance:

- branch is no longer `main`
- `git status` shows only in-scope files for the PR

### Milestone 2: Align Minimal Artifacts

Subsystem: docs only

- add merge-ready planning artifacts for this PR
- add a separate `production-like verification` milestone artifact
- avoid any docs text that claims live production-like readiness

Acceptance:

- PR docs explain current scope, post-merge verification, and reviewer focus
- production-like verification is explicitly separate from the current PR work

### Milestone 3: Verification And PR Packaging

Subsystem: tests and PR metadata

- run the local baseline checks for the narrowed branch
- capture reviewer risks and checks
- prepare final PR title and PR description text

Acceptance:

- `ruff check .` passes
- `pytest -q` passes
- final branch state is ready to open as a PR
