# Implementation Plan: Objective MVP/Demo Project Stage Status

Status: approved for execution on `2026-03-19`.

## Summary

- Goal: produce an objective, evidence-first readiness status for NETvRF as an `MVP/demo`, not as a production release.
- Output shape: a two-layer audit that evaluates the last verified baseline separately from the current dirty local WIP.
- Scope: `docs/artifacts` only. No application code, tests, infra config, or runtime behavior changes.

## Source Priority

1. current code and current local command results
2. dated verification artifacts in `docs/artifacts/*`
3. `docs/project_brief.md`
4. `README.md`

Note: before this milestone, `docs/artifacts/project_stage_status.md` was not tracked in the repository and therefore could not be used as a source of truth.

## Milestone 1: Produce The Objective Status Audit

Subsystem: `docs/artifacts`

### Inputs

- repository structure and mounted routes from `app/main.py`, `app/api/router.py`, and `app/web/routes.py`
- runtime/config wiring from `app/core/config.py`, `app/api/deps.py`, `app/db/session.py`, `app/tasks/*`
- CI and package/test wiring from `.github/workflows/ci.yml` and `pyproject.toml`
- current working tree state from `git status --short` and `git diff --stat`
- current local verification results from:
  - `.venv/bin/ruff check .`
  - `.venv/bin/pytest -q tests/api`
  - `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core`
  - `.venv/bin/pytest -q`
- dated runtime evidence from:
  - `docs/artifacts/runtime_verification.md`
  - `docs/artifacts/production_like_verification.md`
  - milestone 5/6/7 walkthrough artifacts

### Deliverables

1. `docs/artifacts/project_stage_status.md`
   - executive verdict
   - verified baseline status
   - current WIP status
   - demo flow audit
   - allowed vs disallowed claims
   - blockers and remaining gaps
   - priority next steps

2. `docs/artifacts/walkthrough_project_stage_status.md`
   - changed files
   - commands run
   - tests run
   - audit notes and evidence boundaries

### Evaluation Rubric

- `green`: directly confirmed by current code and/or current local runs, or by a dated artifact with exact commands and no contradiction
- `yellow`: implemented and partially evidenced, but the claim boundary must stay narrow
- `red`: absent, broken, or not safe to rely on for demo claims
- `grey`: source missing or evidence insufficient

Every rated block must include:

- `evidence`
- `claim boundary`
- `risk`
- `next step`

### Acceptance Criteria

- the report is written in Russian
- the report is evidence-first and avoids marketing language
- baseline and WIP are separated rather than averaged
- current local command results are quoted exactly
- CI scope is described exactly as it exists today
- public API and web UI interfaces are explicitly covered
- the `2026-03-19` production-like artist sync snapshot is included as a bounded claim, not as blanket live readiness
- the report explicitly distinguishes safe demo flows from conditional or non-claimable ones

## Constraints

- do not change application behavior
- do not invent runtime claims that are not supported by current code or dated evidence
- keep the diff compact and limited to `docs/artifacts`
