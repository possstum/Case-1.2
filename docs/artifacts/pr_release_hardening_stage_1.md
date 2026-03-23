## Summary

This PR closes the immediate Stage 1 release-hardening gaps on top of the current `yandex-catalog-ingest-pr` branch without widening the certified runtime scope.

Before this change, the branch had useful live and staging-like evidence, but the demo story still depended too much on fresh search results and loosely aligned verification docs. That made operator handoff brittle: detail pages and job pages did not have one deterministic seeded path, and the current exact-branch claims were spread across older artifacts with stale dirty-worktree language.

The root cause was not one runtime bug. It was a release-readiness packaging gap:

- there was no reusable runtime-safe demo seed module with fixed IDs
- there was no single exact-branch verification artifact for the current certified SHA
- the current stage-status and production-like docs still mixed historical evidence with newer branch-state claims

This PR fixes that by introducing a deterministic seeded demo bootstrap and by tightening the docs around the exact verified scope.

## What Changed

- added `app.demo` runtime seed data and a `python -m app.demo.seed` entrypoint with fixed seeded artist/release/track/job identifiers
- added `scripts/reset_seeded_demo_env.sh` so the demo environment can be reset into a deterministic state
- added `scripts/run_demo_worker.sh` so the worker uses the same isolated demo database and Redis shape as the demo API
- moved the old synthetic demo setup out of the oversized test helper and covered the seeded path with focused tests in `tests/demo/test_seed.py`
- recorded exact-branch verification in `docs/artifacts/exact_branch_verification_2026_03_20.md`
- updated `docs/artifacts/project_stage_status.md` and `docs/artifacts/production_like_verification.md` so current claims stay narrow and tied to dated evidence
- added delivery artifacts for the branch push / PR workflow in `docs/artifacts/implementation_plan_branch_push_pr.md` and `docs/artifacts/walkthrough_branch_push_pr.md`

## User Impact

For operators, there is now a deterministic demo path that does not rely on luck in live provider search before showing entity detail and job pages. For reviewers and future handoff, the current branch claims are easier to audit because they point to one exact-branch verification artifact and one constrained stage-status document.

For end users, the certified live story is still intentionally narrow. This PR does not claim broad live-provider readiness, deploy readiness, or public-internet readiness. It keeps the verified live scope limited to the exact certified pair `Krovostok` and `Motorama`, while adding a stable seeded demo fallback for fixed IDs.

## Validation

- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q`
- `.venv/bin/pytest -q tests/demo/test_seed.py tests/api/test_entities.py tests/api/test_web_ui.py tests/api/test_sync_jobs.py`
- `sh -n scripts/reset_seeded_demo_env.sh`
- `sh -n scripts/run_demo_worker.sh`
- `./scripts/reset_seeded_demo_env.sh`
- `DEMO_LOAD_DOTENV=0 ./scripts/run_demo_api.sh`
- runtime probes for seeded `/health`, detail routes, job route, and UI pages
- live production-like probes for `Krovostok` and `Motorama` through `/search`, `/sync/artist/{id}`, `/jobs/{job_id}`, and post-sync artist/UI checks

## Out Of Scope

- Docker/deployment automation
- public internet exposure
- TLS termination
- app-level auth
- generalized claims about arbitrary live provider quality or reliability
