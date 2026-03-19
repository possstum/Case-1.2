# Project Stage Status: Objective MVP/Demo Readiness Audit

Status: captured on `2026-03-19`.

## Summary

Этот документ оценивает NETvRF только как `MVP/demo`. Это не production-readiness review и не PR approval.

Методика:

1. current code and current local command results
2. dated verification artifacts in `docs/artifacts/*`
3. `docs/project_brief.md`
4. `README.md`

Important source note:

- до этого аудита `docs/artifacts/project_stage_status.md` не был tracked в репозитории, поэтому не мог использоваться как source of truth
- этот artifact создан именно для закрытия этой doc gap, но historical doc drift по другим artifacts остается отдельным риском

## Current Fact Snapshot

### Current Local Verification Results

| Command | Current result |
| --- | --- |
| `.venv/bin/ruff check .` | `All checks passed!` |
| `.venv/bin/pytest -q tests/api` | `42 passed in 2.72s` |
| `.venv/bin/pytest -q tests/services tests/providers tests/db tests/utils tests/core` | `59 passed in 1.19s` |
| `.venv/bin/pytest -q` | `107 passed in 3.55s` |

### Current Repository State

| Fact | Current observation |
| --- | --- |
| CI scope | `.github/workflows/ci.yml` runs install, `ruff check .`, `pytest -q tests/api`, `pytest -q tests/services tests/providers tests/db tests/utils tests/core` |
| Dirty worktree | `git diff --stat` shows `20 files changed`, `2268 insertions`, `116 deletions` |
| Public API routes mounted | `/health`, `/search`, `/artists/{artist_id}`, `/releases/{release_id}`, `/tracks/{track_id}`, `/sync/{kind}/{target_id}`, `/jobs/{job_id}` |
| Public web routes mounted | `/`, `/ui`, `/ui/artists/{artist_id}`, `/ui/releases/{release_id}`, `/ui/tracks/{track_id}`, `/ui/sync/{kind}/{target_id}`, `/ui/jobs/{job_id}` |
| Alembic revision count | `5` tracked revision files in `alembic/versions` |
| Historical missing source | before this audit, tracked `docs/artifacts/project_stage_status.md` was absent |

## Executive Verdict

### Overall Verdict

Objectively, the project is already well beyond scaffold stage. The honest label is:

`expanded MVP with conditional demo readiness`

That means:

- the project is strong enough for a controlled demo with known routes, known IDs, and narrow claims
- the project is not strong enough for broad claims about arbitrary live search quality, arbitrary live sync success, or production deployment readiness

### Layer Verdicts

| Layer | Verdict | Rationale |
| --- | --- | --- |
| Verified baseline | `yellow` leaning `green` | core API/UI/runtime baseline is real, current local verification is green, staging-like verification exists, and one dated production-like artist sync snapshot exists; live-provider claims still need a narrow boundary |
| Current local WIP | `yellow` leaning `green` | the WIP now has a fresh exact-branch search-first runtime artifact for `Motorama` and `Krovostok`, and the full test suite is green; it still remains dirty, cross-subsystem, and not broadly runtime-certified beyond the exact certified query set |

### Search-First Certification Update

Fresh current-WIP evidence now exists for a narrow first-user launch story:

- clean demo reset succeeded through `./scripts/reset_demo_env.sh`
- host-run demo API started through `./scripts/run_demo_api.sh`
- parallel cold-start `Motorama` `/search` and `/ui` both returned `200`
- warm `Motorama` `/search` and `/ui` both returned `200`
- cold and warm `Krovostok` `/search` and `/ui` both returned `200`
- the previous duplicate provider-row `IntegrityError` did not recur

Claim boundary for this update:

- safe: exact-query search-first certification for `Motorama` and `Krovostok`
- not safe: generalized live search quality claims beyond those exact verified queries
- not safe: sync/jobs or worker-backed launch claims

### What Can Be Honestly Demoed Now

- `GET /health`
- mounted API and web surfaces
- `/ui` landing and search shell
- search/detail/job routes under controlled conditions
- SQLite WAL local development path
- staging-like PostgreSQL + Redis host-run baseline
- one specifically documented `2026-03-19` production-like artist sync snapshot

### What Must Not Be Overstated

- general live-provider search quality across arbitrary artist queries
- general worker-backed refresh reliability across arbitrary entities
- production deployment readiness
- any claim that the current dirty WIP has already been live-verified end-to-end

## Verified Baseline Status

### Status Matrix

| Block | Status | Evidence | Claim boundary | Risk | Next step |
| --- | --- | --- | --- | --- | --- |
| API surface | `green` | mounted in `app/main.py` and `app/api/router.py`; current API tests are green; dated route probe exists in `docs/artifacts/runtime_verification.md` | safe to claim the API surface exists and the documented routes are wired; success-path detail and sync still depend on existing data or jobs | fresh DB can legitimately return `404` or `503` on some flows | maintain a seeded demo DB with known IDs and known expected responses |
| Web UI surface | `green` | mounted in `app/main.py` and `app/web/routes.py`; current web UI tests are green; runtime artifact documents `/ui` availability and provider-disabled fallback | safe to claim `/ui` exists and renders baseline states; not safe to generalize live query quality from UI alone | live output still depends on provider availability and current registry behavior | keep a scripted demo path with known query and known artist page IDs |
| SQLite WAL dev path | `green` | `app/db/session.py` enables WAL and foreign keys; README and runtime artifact document local flow; current test suite passes on local setup | safe to claim local SQLite development is part of the verified baseline | no statement here proves production concurrency behavior | keep dev smoke commands in sync with actual local verification |
| PostgreSQL + Redis staging-like path | `green` | `docker-compose.yml`, `.env.staging.example`, README, and `docs/artifacts/runtime_verification.md` all document a host-run app against PostgreSQL + Redis | safe to claim a staging-like local topology has been verified with blank tokens | this does not prove deploy automation, production networking, or cloud runtime behavior | add a repeatable scripted smoke job for staging-like startup |
| Sync/jobs API and queue surface | `yellow` | routes exist, tests exist, `app/tasks/queue.py` and `app/tasks/worker.py` are wired, and one dated production-like artist sync snapshot is documented | safe to claim enqueue/status flows exist and one artist sync run on `2026-03-19` finished successfully; not safe to claim generalized live refresh readiness | sync success depends on Redis, worker process, provider behavior, and existing canonical rows | re-run end-to-end sync verification on the exact current WIP and keep exact job payload evidence |
| Yandex catalog ingest | `yellow` | service exists in `app/services/yandex_catalog_service.py`; tests are green; `docs/artifacts/production_like_verification.md` documents post-sync Yandex catalog evidence | safe to claim the subsystem exists and one documented artist-sync path surfaced Yandex catalog data after refresh | broader live-provider coverage remains partial; evidence is narrow and artist-specific | capture at least one second live artist case or keep claims artist-specific |
| Logging and secret redaction | `green` | `app/core/logging.py` implements redaction; `tests/core/test_logging.py` is green; runtime artifact includes redaction smoke | safe to claim Authorization/Cookie/token-like values are masked in the verified baseline | logging correctness does not prove every future log call avoids risky payloads | keep redaction tests when provider/logging code changes |
| Migrations and schema | `green` | Alembic is wired; current test suite is green; `tests/db/test_migrations.py` verifies canonical/platform/cache/job schema expectations; `5` revision files exist | safe to claim the schema baseline exists for canonical entities, platform entities, cache, jobs, and Yandex catalog storage | schema correctness does not by itself prove data quality or runtime completeness | keep migration tests aligned with every schema change |
| CI/local verification baseline | `green` | `.github/workflows/ci.yml` matches the current local baseline commands and those commands are green right now | safe to claim lint + pytest baseline is green now | CI does not cover live runtime, deploy, Docker image build, or full staging-like smoke | add runtime smoke or artifact freshness checks to CI |
| Docs fidelity | `yellow` | README and `docs/project_brief.md` broadly align with current code; dated runtime/production-like artifacts exist | safe to use docs only when bounded by exact dates and exact artifacts | historical artifacts disagree on test counts and some claims are distributed across multiple files | keep this file as canonical status summary and treat older artifacts as historical evidence, not live truth |

### Verified Baseline Readiness Readout

- Strongest baseline area: local code health, route surface, schema, tests, and staging-like host-run verification.
- Weakest baseline area: live provider behavior beyond one documented artist sync snapshot.
- Honest baseline demo stance: `controlled demo is viable`, `broad live claim is not`.

## Current WIP Status

### What The Current Diff Adds Over The Verified Baseline

Observed from current dirty worktree:

- artist detail now exposes `yandex_catalog_sections`
- artist detail now exposes `missing_on_yandex_view`
- `/ui` now promotes a primary artist CTA via `Open artist overview`
- artist search cache keying moved from `search:v1` to `search:v2`
- artist search now applies query-aware reranking for deterministic artist results
- current WIP also touches provider clients, worker/queue behavior, docs, and tests

### WIP Readiness Verdicts

| Dimension | Status | Evidence | Claim boundary | Risk | Next step |
| --- | --- | --- | --- | --- | --- |
| Functional readiness | `yellow` | current full suite is green with `105 passed`; diff adds targeted tests for artist rerank, artist detail enrichment, and web UI artist overview rendering | safe to say the WIP looks internally consistent under automated coverage | green tests are not equivalent to a fresh live runtime proof for this exact diff | run the exact current worktree through staging-like and production-like verification again |
| Merge/demo discipline readiness | `red` | dirty worktree spans services, providers, worker, web UI, docs, and tests; diff is large and cross-subsystem | not safe to describe this WIP as a compact, merge-ready, single-subsystem slice | integration regression risk is materially higher; failure attribution is harder | split or re-verify the current branch into smaller explainable slices |
| Search rerank changes | `green` | `app/services/search_service.py` diff plus new search tests verify `search:v2` cache keys and artist reranking behavior | safe to claim the logic is covered by current automated tests | no fresh live-provider runtime artifact proves arbitrary real-query behavior for this exact code | capture exact live probes for the known accepted queries on the exact current branch |
| Artist overview enrichment | `yellow` | `app/services/artist_service.py`, `app/web/render.py`, `tests/api/test_entities.py`, and `tests/api/test_web_ui.py` show API/UI support for Yandex-native sections and missing-on-Yandex view | safe to claim the feature exists in code and tests | current dirty WIP does not yet have a fresh production-like artifact proving these exact renderings in live runtime | rerun artist overview runtime verification after freezing the branch |
| Worker/queue changes in WIP | `yellow` | `app/tasks/queue.py` and `app/tasks/worker.py` changed, and tests are green | safe to claim the code changed and the suite stayed green | no fresh current-WIP live worker artifact exists | re-run worker-backed sync on this exact diff and attach exact job/result evidence |
| Docs alignment for WIP | `yellow` | README and brief were updated, but the branch remained dirty and claims still depend on historical artifacts | safe to say docs are moving toward the newer `2026-03-19` state | doc drift can reappear when code and historical artifacts move at different speeds | treat this file as the current top-level status source and backfill exact WIP runtime evidence |

### Current WIP Readiness Readout

- The WIP is stronger than the last published baseline for the artist-centric demo.
- The WIP is not yet strong enough to replace the verified baseline as the sole demo truth.
- Honest WIP stance: `promising and test-green`, `not yet fully runtime-certified`.

## Demo Flow Audit

### Flow Matrix

| Flow | Verified baseline | Current WIP | Evidence | Claim boundary |
| --- | --- | --- | --- | --- |
| app startup and `GET /health` | `safe to demo` | `safe to demo` | app wiring exists; health service exists; runtime and staging-like artifacts exist | safe for both local and staging-like baseline; says nothing about cloud deployment |
| `GET /ui` landing | `safe to demo` | `safe to demo` | web routes mounted; web UI tests green; empty/provider-disabled states documented | safe to claim landing and shell availability |
| artist search | `conditionally safe` | `conditionally safe` | search route exists; rate limit and cache paths are tested; WIP rerank tests are green; live search verification remains partial | safe only with bounded claims and preferably known queries |
| artist overview | `conditionally safe` | `conditionally safe` with richer WIP | detail route exists; WIP adds Yandex catalog and missing-on-Yandex sections with tests | safe when known canonical IDs and expected data are present |
| release detail | `conditionally safe` | `conditionally safe` | route and tests exist | safe only when known canonical IDs already exist in the active DB |
| track detail | `conditionally safe` | `conditionally safe` | route and tests exist | safe only when known canonical IDs already exist in the active DB |
| sync enqueue | `conditionally safe` | `conditionally safe` | route exists, tests exist, queue scheduler exists | safe to show `202` or acceptable `404`, but not to generalize provider refresh success |
| job status | `conditionally safe` | `conditionally safe` | route exists, tests exist, documented job states exist | safe for known job IDs; unknown IDs may correctly return `404` |
| worker-backed refresh evidence | `conditionally safe` | `not safe to claim` as current-WIP generality | one dated `2026-03-19` production-like artist sync artifact exists; current WIP lacks a fresh exact rerun | safe only as one historical, exact, dated artist-sync example |

### Practical Demo Interpretation

- safest demo: health, UI shell, controlled search, known artist page, known job page
- acceptable but conditional demo: sync enqueue followed by job polling, if the environment matches the documented working setup
- unsafe demo claim: "live search and sync are generally solved now"

## Claims We Can Make

- NETvRF is a real FastAPI MVP with mounted API and web UI routes for health, search, details, sync, and job status.
- The local development baseline is real and green right now: `ruff`, API tests, non-API tests, and the full test suite all pass.
- SQLite WAL development is wired in the codebase and part of the verified local baseline.
- A staging-like host-run app against PostgreSQL + Redis is documented and was previously verified with exact commands.
- The project includes queue-backed sync wiring with a separate RQ worker process.
- Yandex catalog ingestion exists in code and has targeted automated coverage.
- There is one specifically documented production-like artist sync snapshot dated `2026-03-19` where `/jobs/{job_id}` finished and post-sync Yandex catalog evidence remained visible.
- The current local WIP strengthens the artist-centric demo path with deterministic artist reranking, primary artist CTA behavior, and richer artist detail payloads.

## Claims We Must Not Make

- "Live provider search is fully verified."
- "Arbitrary artist queries now reliably resolve correctly in live runtime."
- "Worker-based refresh is broadly proven across providers and entity types."
- "The current dirty WIP has already been fully runtime-verified."
- "The project is production-ready."
- "CI covers deployment or production-like runtime validation."
- "Docker image build and staging deployment are part of the verified pipeline."

## Boundary Between One Verified Snapshot And General Live Readiness

The strongest live claim supported today is narrow:

- on `2026-03-19`, one production-like artist sync path was documented with both providers updated, job status `finished`, and Yandex catalog evidence still visible after sync

That does **not** expand into:

- general live search readiness
- general live refresh readiness
- provider-wide reliability across arbitrary queries or entities

## Blockers And Remaining Gaps

| Gap | Status | Evidence | Risk | Next step |
| --- | --- | --- | --- | --- |
| Broader live-provider verification | `yellow` blocker | production-like evidence is narrow and artist-specific; milestone 6/7 artifacts also record environment/runtime blockers for wider live verification | demo claims can outrun evidence | rerun live verification on the exact current branch with exact commands and preserved outputs |
| No deploy workflow / no staging target automation | `red` blocker | README already states CI has no staging deploy; repo has no deployment workflow | demo can work while release path remains undefined | decide on deployment target and add a real deployment pipeline |
| No application Docker build path | `red` blocker | repo has infra `docker-compose.yml` but no app `Dockerfile`; CI does not build an image | runtime reproducibility outside local host-run setup is weaker | add Docker build only when a real deployment strategy is chosen |
| Separate worker dependency | `yellow` blocker | sync success depends on Redis plus separate RQ worker process | demo can fail operationally even when API is healthy | script combined API/worker demo startup and health checks |
| Dirty multi-subsystem WIP | `yellow` blocker | `20 files changed` across multiple app/test/doc subsystems | exact demo behavior is harder to freeze and explain | freeze the branch or split it into small verified slices |
| Historical docs drift | `yellow` blocker | older artifacts disagree on exact test counts and live boundaries | audiences can read outdated confidence signals | treat this file as the current status summary and keep older artifacts explicitly historical |
| Previously missing tracked stage-status source | `resolved in this milestone` | before this audit the file was absent; this artifact now exists | without maintenance it can drift again | keep this file updated whenever runtime claims or baseline counts change |

## Priority Next Steps

1. Re-run staging-like and production-like verification on the exact current dirty WIP after freezing it into a reproducible branch state.
2. Prepare a seeded demo environment with known canonical artist, release, track, and job IDs so the demo does not depend on fresh lookup luck.
3. Capture exact live probes for the current deterministic artist search behavior on the known accepted queries.
4. Reduce the current multi-subsystem WIP into smaller, explainable milestones or regenerate a single fresh verification artifact that covers the exact combined diff.
5. Keep this file as the canonical status summary and demote older status statements to dated historical evidence.
6. Only after the current branch is runtime-reverified should README and project brief make stronger claims about the richer artist overview flow.
