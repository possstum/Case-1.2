# Walkthrough: Objective MVP/Demo Project Stage Status

Status: completed on `2026-03-19`.

## Goal

Create a tracked, evidence-first project status artifact for NETvRF that rates MVP/demo readiness in two layers:

- last verified baseline
- current dirty local WIP

## Scope

- `docs/artifacts/implementation_plan_project_stage_status.md`
- `docs/artifacts/project_stage_status.md`
- `docs/artifacts/walkthrough_project_stage_status.md`

Out of scope:

- `app/*`
- `tests/*`
- `.github/*`
- infra/runtime changes
- any change to application behavior

## Milestone Log

### Milestone 1: Docs/Artifacts Status Audit

Changed files:

- `docs/artifacts/implementation_plan_project_stage_status.md`
- `docs/artifacts/project_stage_status.md`
- `docs/artifacts/walkthrough_project_stage_status.md`

Commands run:

- `pwd`
- `rg --files -g 'README.md' -g 'docs/**' -g 'pyproject.toml' -g 'requirements*.txt' -g 'Dockerfile*' -g 'docker-compose*.yml' -g 'alembic.ini' -g '.env*' -g 'Makefile' -g 'package.json'`
- `git status --short`
- `sed -n '1,220p' docs/project_brief.md`
- `sed -n '1,260p' README.md`
- `sed -n '1,260p' docs/artifacts/runtime_verification.md`
- `sed -n '1,260p' docs/artifacts/production_like_verification.md`
- `sed -n '1,220p' .github/workflows/ci.yml`
- `sed -n '1,260p' pyproject.toml`
- `test -x .venv/bin/pytest && echo PYTEST_READY || echo PYTEST_MISSING`
- `test -x .venv/bin/ruff && echo RUFF_READY || echo RUFF_MISSING`
- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q tests/api`
- `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core`
- `.venv/bin/pytest -q`
- `git diff --stat`
- `git log --oneline -5`
- `sed -n '1,260p' docs/artifacts/frontend_artist_mvp_remaining_steps.md`
- `sed -n '1,260p' docker-compose.yml`
- `sed -n '1,260p' .env.staging.example`
- `sed -n '1,240p' app/main.py`
- `sed -n '1,240p' app/api/router.py`
- `sed -n '1,260p' app/core/config.py`
- `sed -n '1,260p' app/tasks/queue.py`
- `sed -n '1,260p' app/tasks/worker.py`
- `sed -n '1,260p' app/web/routes.py`
- `sed -n '1,320p' app/api/deps.py`
- `sed -n '1,260p' scripts/run_api.sh`
- `sed -n '1,240p' scripts/run_worker.sh`
- `sed -n '1,260p' app/core/logging.py`
- `sed -n '1,260p' app/utils/rate_limit.py`
- `sed -n '1,260p' app/db/session.py`
- `sed -n '1,220p' app/services/health_service.py`
- `sed -n '1,220p' tests/db/test_migrations.py`
- `sed -n '1,240p' tests/core/test_logging.py`
- `find alembic/versions -maxdepth 1 -type f | wc -l`
- `rg -n "@router\\.(get|post|put|delete|patch)" app/api/routes app/web/routes.py`
- `rg -n "def test_" tests | wc -l`
- `rg -n "TODO|FIXME|XXX|HACK|TBD|unverified|partial|remaining" app tests docs README.md .github -g '!docs/artifacts/walkthrough*' -g '!docs/artifacts/implementation_plan*'`
- `sed -n '1,260p' docs/artifacts/implementation_plan_frontend_artist_mvp_phase_2.md`
- `sed -n '1,260p' docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_5_deterministic_artist_search_for_live_queries.md`
- `sed -n '1,260p' docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_6_live_runtime_verification_for_deterministic_artist_search.md`
- `sed -n '1,260p' docs/artifacts/walkthrough_frontend_artist_mvp_phase_2_milestone_7_runtime_precondition_unblock_for_live_deterministic_artist_search_verification.md`
- `rg -n "yandex_catalog_sections|Yandex native catalog|Missing on Yandex|direct albums|deterministic|primary CTA|artist overview" app/services/artist_service.py app/web/render.py tests/api/test_web_ui.py tests/api/test_entities.py tests/api/test_search.py README.md docs/project_brief.md`
- `git diff --unified=0 -- app/services/artist_service.py app/web/render.py tests/api/test_web_ui.py README.md docs/project_brief.md | sed -n '1,320p'`
- `git diff --unified=0 -- app/services/search_service.py tests/api/test_search.py | sed -n '1,320p'`

Tests run:

- `.venv/bin/ruff check .`
  - result: `All checks passed!`
- `.venv/bin/pytest -q tests/api`
  - result: `41 passed in 3.08s`
- `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core`
  - result: `58 passed in 1.31s`
- `.venv/bin/pytest -q`
  - result: `105 passed in 4.09s`

Key audit findings captured into the status artifact:

- the project is objectively past scaffold stage and is best described as `expanded MVP with conditional demo readiness`
- the last verified baseline is stronger than a health-only demo and includes one dated production-like artist sync snapshot on `2026-03-19`
- the current dirty WIP appears functionally stronger for artist-centric demos, but that exact diff has not yet been fully runtime-certified
- CI is narrow by design and currently covers lint plus two pytest groups only
- deploy/runtime automation remains outside the verified baseline
- historical docs contain drift, so the new `project_stage_status.md` should be treated as the top-level status summary going forward

## Final Outcome

- created the required Implementation Plan artifact first
- created a tracked `docs/artifacts/project_stage_status.md` source that did not previously exist in the repository
- kept the milestone limited to the `docs/artifacts` subsystem
- did not mutate application code, tests, infra, or runtime wiring
