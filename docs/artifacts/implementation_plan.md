# Implementation Plan: Minimal CI Baseline Without Duplicate Pytest Coverage

Status: approved and implemented on `2026-03-16`.

## Summary

- Simplify `.github/workflows/ci.yml` to the intended two-command pytest baseline and keep `ruff check .` unchanged.
- Remove both sources of duplicate coverage:
  - the standalone `tests/api/test_web_ui.py` step, because that file is already inside `tests/api`
  - the aggregate `tests/api tests/services tests/providers tests/db tests/utils tests/core` step, because it reruns API coverage and most non-API coverage
- Align the baseline documentation in `README.md`, `docs/project_brief.md`, and `docs/artifacts/runtime_verification.md` to the same minimal CI shape.
- Append short notes to `docs/artifacts/walkthrough.md` instead of rewriting prior historical entries.
- Do not change runtime application code, add a `Dockerfile`, add an image build, add deploy logic, or add any live-provider claim.

## Public APIs / Interfaces / Types

- No runtime API, schema, ORM, migration, queue, worker, or web UI contract changes.
- The only interface change is the CI workflow test surface in `.github/workflows/ci.yml`:
  - keep `ruff check .`
  - keep `pytest -q tests/api`
  - keep `pytest -q tests/services tests/providers tests/db tests/utils tests/core`
  - remove any standalone `tests/api/test_web_ui.py` or aggregate full-baseline pytest step

## Milestone 1: CI Workflow Deduplication

Files:

- `.github/workflows/ci.yml`
- `docs/artifacts/implementation_plan.md`

Edits:

- Keep the existing workflow name, triggers, single job, Ubuntu runner, Python `3.9`, and pip cache.
- Keep dependency installation as `python -m pip install -e '.[dev]'`.
- Keep the lint step exactly as `ruff check .`.
- Replace the four current pytest steps with exactly two pytest steps in this order:
  - `pytest -q tests/api`
  - `pytest -q tests/services tests/providers tests/db tests/utils tests/core`
- Remove the standalone `pytest -q tests/api/test_web_ui.py` step.
- Remove the aggregate `pytest -q tests/api tests/services tests/providers tests/db tests/utils tests/core` step.
- Rename the remaining pytest steps to be short and explicit:
  - `Run pytest api baseline`
  - `Run pytest non-api baseline`
- Do not add a matrix, service containers, Docker/image build, deploy logic, or new tooling.

Validation:

- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core`

Tests:

- same as validation commands above

## Milestone 2: Baseline Docs Sync

Files:

- `README.md`
- `docs/project_brief.md`
- `docs/artifacts/runtime_verification.md`
- `docs/artifacts/walkthrough.md`

Edits:

- Update `README.md` `Verified Local Vs CI Commands` so it contains only the lint row, `pytest -q tests/api`, and `pytest -q tests/services tests/providers tests/db tests/utils tests/core`.
- Remove the separate `pytest web ui` row and the aggregate full-baseline pytest row from `README.md`.
- Update `docs/artifacts/runtime_verification.md` `Commands Actually Run`, `Exact Local Results`, and `Verified Behavior Matrix` to the two-command baseline.
- Record the minimal-baseline rerun outputs from implementation verification:
  - `tests/api` -> `24 passed`
  - `tests/services tests/providers tests/db tests/utils tests/core` -> `28 passed`
- Update section `13. Какие тесты есть и что они реально покрывают` in `docs/project_brief.md` so the “Verified local CI-aligned results” paragraph references only the two remaining commands.
- Append new short sections to `docs/artifacts/walkthrough.md` instead of editing prior milestone history.

Validation:

- `rg -n "test_web_ui.py|pytest -q tests/api tests/services|pytest full baseline|web ui pytest baseline" README.md docs/project_brief.md docs/artifacts/runtime_verification.md .github/workflows/ci.yml`
- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core`

Tests:

- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core`

## Acceptance Scenarios

1. `.github/workflows/ci.yml` contains `ruff check .` and exactly two pytest commands.
2. `.github/workflows/ci.yml` contains no direct reference to `tests/api/test_web_ui.py`.
3. `.github/workflows/ci.yml` contains no aggregate `pytest -q tests/api tests/services tests/providers tests/db tests/utils tests/core` step.
4. The remaining two pytest commands match the preferred target shape exactly:
   - `pytest -q tests/api`
   - `pytest -q tests/services tests/providers tests/db tests/utils tests/core`
5. `README.md`, `docs/project_brief.md`, and `docs/artifacts/runtime_verification.md` all describe the same two-command baseline.
6. `docs/artifacts/walkthrough.md` gets only short append-only notes for this change.
7. No application code, no tests, no tooling config beyond CI/docs, and no Docker/image build changes are introduced.

## Assumptions And Defaults

- `tests/api/test_web_ui.py` stays covered implicitly via `tests/api`; there is no separate CI reason to keep it isolated.
- `tests/core` belongs in the non-API baseline and stays in the retained second pytest command.
- `docs/project_brief.md` is in scope because it repeated the old four-command “CI-aligned” story.
- Walkthrough history remains append-only; older milestone text is not retroactively rewritten.
- Timing values in verification docs come from the implementation rerun, with pass counts expected to remain `24` and `28`.
