# Project Stage Status: Objective MVP/Demo Readiness Audit

Status: updated on `2026-03-23`.

## Summary

Этот документ оценивает NETvRF как `MVP/demo` после закрытия Stage 1 release hardening. Это не production-readiness review и не PR approval.

Главный вывод:

`controlled demo-ready MVP on exact certified scope`

Это значит:

- можно честно показывать seeded demo path с фиксированными ID
- можно честно показывать live artist search + sync только для exact certified pair: `Krovostok` и `Motorama`
- нельзя честно заявлять deploy readiness, public internet readiness, broad live-provider readiness или generalized worker/sync reliability

Canonical source for current runtime claims:

- [exact_branch_verification_2026_03_20.md](/Users/possstum/Documents/WorkID2/docs/artifacts/exact_branch_verification_2026_03_20.md)

## Current Fact Snapshot

### Current Local Verification Results

| Command | Current result |
| --- | --- |
| `.venv/bin/ruff check .` | `All checks passed!` |
| `.venv/bin/pytest -q` | `118 passed in 5.26s` |

### Current Repository State

| Fact | Current observation |
| --- | --- |
| Frozen verification target | exact branch tip `0e911d2fd123e472b2aa661fd06a8f2fac009747` on `yandex-catalog-ingest-pr` |
| Current local worktree | Stage 1 implementation diff is now layered locally on top of that frozen tip until commit |
| Public API routes mounted | `/health`, `/search`, `/artists/{artist_id}`, `/releases/{release_id}`, `/tracks/{track_id}`, `/sync/{kind}/{target_id}`, `/jobs/{job_id}` |
| Public web routes mounted | `/`, `/ui`, `/ui/artists/{artist_id}`, `/ui/releases/{release_id}`, `/ui/tracks/{track_id}`, `/ui/sync/{kind}/{target_id}`, `/ui/jobs/{job_id}` |
| Seeded demo IDs | `artist_id=910001`, `release_id=920001`, `track_id=930001`, `job_id=00000000-0000-4000-8000-000000910001` |
| Live certified artist pair | `Krovostok` and `Motorama` |
| Alembic revision count | `5` tracked revision files in `alembic/versions` |

## Executive Verdict

### Overall Verdict

The honest label now is:

`controlled launch candidate for trusted-network demo use`

That means:

- seeded detail/job/UI routes are deterministic and runtime-verified
- exact live search + sync for `Krovostok` and `Motorama` are runtime-verified on the current branch tip
- the project is still not deploy-ready and still not certified for arbitrary live artist/provider behavior

### Layer Verdicts

| Layer | Verdict | Rationale |
| --- | --- | --- |
| Verified baseline | `green` | lint, full test suite, seeded staging-like path, and narrow live production-like path are all now documented on exact dated evidence |
| Current exact branch tip | `green` within narrow scope | the exact certified scope is now runtime-backed, but still intentionally narrow and non-deployable |
| Deployability | `red` | no application Docker image, no staging deployment automation, no public entrypoint hardening |

## Exact Certified Scope

### What Is Runtime-Certified Now

| Capability | Verdict | Evidence | Claim boundary |
| --- | --- | --- | --- |
| `GET /health` | `safe to demo` | seeded and live runs both returned `200` in the exact-branch artifact | safe for local and staging-like host-run demos |
| seeded artist/release/track/job routes | `safe to demo` | deterministic seeded IDs returned `200` on API and UI routes | safe only for the fixed seeded IDs documented above |
| blank-token staging-like demo path | `safe to demo` | `./scripts/reset_seeded_demo_env.sh` plus `DEMO_LOAD_DOTENV=0 ./scripts/run_demo_api.sh` was re-verified | safe only for seeded known IDs; blank-token `/search` is still environment-sensitive |
| live search for `Krovostok` | `safe to demo` | `/search?q=Krovostok&kind=artist&limit=5` returned `200`, then sync completed successfully | safe only for this exact query and current provider state |
| live search for `Motorama` | `safe to demo` | `/search?q=Motorama&kind=artist&limit=5` returned `200`, then sync completed successfully | safe only for this exact query and current provider state |
| worker-backed artist sync for `Krovostok` | `safe to demo` | `POST /sync/artist/4` returned `202`, `/jobs/...` reached `finished`, `partial=false`, both providers `updated` | safe only for this exact artist sync path |
| worker-backed artist sync for `Motorama` | `safe to demo` | `POST /sync/artist/2` returned `202`, `/jobs/...` reached `finished`, `partial=false`, both providers `updated` | safe only for this exact artist sync path |
| post-sync artist overview rendering | `safe to demo` | `/artists/{id}` and `/ui/artists/{id}` stayed healthy after sync for both certified artists | safe only for the seeded artist and the two exact certified live artists |

### What Is Still Not Certified

- arbitrary live artist queries beyond `Krovostok` and `Motorama`
- arbitrary worker-backed refreshes across other entities or providers
- any deploy target or reproducible container build path
- public internet exposure, TLS termination, and app-level auth

## Verified Baseline Status

| Block | Status | Evidence | Risk | Next step |
| --- | --- | --- | --- | --- |
| API surface | `green` | routes are mounted and exact seeded/live probes are documented | detail and sync correctness still depend on data/provider state outside certified scope | keep demo paths tied to known IDs and exact certified queries |
| Web UI surface | `green` | `/ui` and entity/job pages are covered by tests and seeded/live verification | arbitrary live query quality is still not proven | keep UI demo paths bounded to seeded IDs and certified artists |
| SQLite WAL dev path | `green` | code and tests still support the local dev baseline | this says nothing about cloud/runtime packaging | leave dev flow unchanged |
| PostgreSQL + Redis staging-like path | `green` | seeded blank-token run was re-verified on `2026-03-23` | blank-token search behavior can still vary by external provider availability | keep the seeded path as the default deterministic demo |
| Sync/jobs API and queue surface | `green` within narrow scope | two live artist sync flows finished successfully on the exact branch | broader queue/provider coverage remains unproven | extend live matrix only in a separate follow-up milestone |
| Yandex catalog ingest | `green` within narrow scope | both certified artists finished with Yandex `mode="catalog_ingest"` and kept artist overview sections | this is still not provider-wide certification | expand only with additional explicit artist cases |
| Logging and secret redaction | `green` | code/test baseline remains green; seed path did not print token values | future logging changes can still regress | keep redaction tests whenever provider/logging code changes |
| Migrations and schema | `green` | Alembic/test baseline stayed green during Stage 1 | schema health does not equal deployment readiness | add deploy-oriented packaging separately |
| CI/local verification baseline | `green` | current local baseline is `ruff` + `118 passed` | CI still does not cover runtime smoke, Docker build, or deploy | add those only in Stage 2+ |
| Docs fidelity | `yellow` | canonical runtime status is now centralized in the exact-branch artifact and this file | older artifacts remain historical and can be misread if taken as live truth | keep this file and the exact-branch artifact updated together |

## Demo Flow Audit

| Flow | Verdict | Evidence | Claim boundary |
| --- | --- | --- | --- |
| app startup and `GET /health` | `safe to demo` | seeded and live runs both returned `200` | says nothing about cloud deployment |
| `GET /ui` landing and shell | `safe to demo` | route/tests remain green; exact seeded/live environment stayed healthy | shell availability is not evidence of broad search quality |
| seeded artist overview | `safe to demo` | `/artists/910001` and `/ui/artists/910001` returned `200` with expected sections | safe only for the fixed seeded IDs |
| seeded job detail | `safe to demo` | `/jobs/00000000-0000-4000-8000-000000910001` and `/ui/jobs/...` returned `200` with finished state | safe only for the fixed seeded job |
| live artist search | `conditionally safe` | exact-query certification exists for `Krovostok` and `Motorama` | do not generalize beyond those two queries |
| live sync enqueue and job polling | `conditionally safe` | exact artist sync verification passed for artists `4` and `2` | do not generalize beyond those exact artist IDs |
| worker-backed refresh evidence | `conditionally safe` | both live jobs reached `finished` with both providers updated | still narrow; not a general readiness proof |

## Claims We Can Make

- NETvRF is a real FastAPI MVP with mounted API and web UI routes for health, search, details, sync, and job status.
- The current local verification baseline is green: `.venv/bin/ruff check .` and `.venv/bin/pytest -q` passed with `118 passed in 5.26s`.
- A deterministic seeded demo environment now exists with fixed artist, release, track, and job IDs.
- The seeded staging-like path is runtime-verified on the exact branch with blank tokens and known expected outcomes.
- The live search -> sync -> job -> artist/UI path is runtime-verified for `Krovostok` and `Motorama`.
- Both certified live sync jobs reached `finished` with `partial=false` and both providers `status="updated"`.

## Claims We Must Not Make

- "Live provider search is broadly verified."
- "Arbitrary artist queries now resolve reliably in live runtime."
- "Worker-based refresh is proven across providers and entity types."
- "The project is deployment-ready."
- "The project has a reproducible container build path."
- "The current branch is public-internet-ready."

## Boundary Between Exact Certification And General Readiness

The strongest live claim supported now is still narrow:

- on `2026-03-23`, exact-branch production-like verification succeeded for `Krovostok` and `Motorama`
- both artist sync jobs reached `finished`
- both jobs kept `partial=false`
- both jobs reported YouTube `status="updated"` and Yandex `status="updated"`
- post-sync artist overview rendering remained intact for both artists

That does **not** expand into:

- generalized live search readiness
- generalized live refresh readiness
- deploy readiness
- public network readiness

## Blockers And Remaining Gaps

| Gap | Status | Evidence | Risk | Next step |
| --- | --- | --- | --- | --- |
| Broader live-provider verification | `yellow` blocker | Stage 1 certified only `Krovostok` and `Motorama` | claims can outrun evidence if the query set silently expands | certify additional artists only as separate exact-query milestones |
| No deploy workflow / no staging target automation | `red` blocker | repo still has no real deployment workflow | release path remains undefined | add Render staging automation in Stage 2 |
| No application Docker build path | `red` blocker | infra compose exists, but no reproducible app image build exists | runtime portability and deployment reproducibility remain weak | add Dockerfile and build validation in Stage 2 |
| Private-network-only access model | `yellow` blocker | current demo story is still LAN/VPN style without TLS or auth | external testers would require extra hardening | add a public access layer only if external testing is needed |
| Large multi-subsystem diff | `yellow` blocker | the branch still spans app, worker, demo bootstrap, tests, and docs | future regressions are harder to isolate | keep follow-up work split into smaller verified milestones |
| Historical docs drift | `yellow` blocker | older artifacts remain in the repo and are intentionally historical | stale claims can be misread as current truth | keep using this file plus the exact-branch artifact as the canonical status pair |

## Priority Next Steps

1. Add a reproducible application Docker image for FastAPI web/api and RQ worker.
2. Add Render staging deployment automation from the exact verified branch.
3. Decide whether external testing requires a public access layer with TLS termination and app-level auth.
4. Extend live-provider verification beyond `Krovostok` and `Motorama` only as separate exact-query milestones.
5. Keep future changes split into compact, single-subsystem follow-ups instead of another broad combined diff.
