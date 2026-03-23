# Walkthrough: Release Hardening Stage 1

Status: completed on `2026-03-23`.

## Milestone 1: Planning And Branch Freeze Artifact

### Changed Files

- `docs/artifacts/implementation_plan_release_hardening_stage_1.md`
- `docs/artifacts/walkthrough_release_hardening_stage_1.md`
- `docs/artifacts/exact_branch_verification_2026_03_20.md`
- `docs/artifacts/project_stage_status.md`

### Commands Run

```bash
git status -sb
git rev-parse HEAD
git diff --stat $(git merge-base HEAD main)..HEAD
.venv/bin/ruff check .
.venv/bin/pytest -q
```

### Tests Run

- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q`

### Acceptance Result

- Stage 1 artifacts were created for exact branch `0e911d2fd123e472b2aa661fd06a8f2fac009747`.
- The canonical status narrative now targets a clean exact branch tip with a large combined diff, not a dirty worktree.

### Prompt For The Next Milestone

`Реализуй Milestone 2 Stage 1: вынеси synthetic demo seed data в reusable runtime-safe module, добавь .venv/bin/python -m app.demo.seed и ./scripts/reset_seeded_demo_env.sh, затем покрой fixed IDs и seeded detail/job pages тестами и blank-token smoke.`

## Milestone 2: Seeded Demo Bootstrap

### Changed Files

- `app/demo/__init__.py`
- `app/demo/data.py`
- `app/demo/seed.py`
- `scripts/reset_seeded_demo_env.sh`
- `scripts/run_demo_worker.sh`
- `tests/demo/test_seed.py`
- `tests/test_support.py`

### Commands Run

```bash
chmod +x scripts/reset_seeded_demo_env.sh scripts/run_demo_worker.sh
```

```bash
.venv/bin/ruff check app/demo tests/demo/test_seed.py tests/test_support.py
```

```bash
sh -n scripts/reset_seeded_demo_env.sh
```

```bash
sh -n scripts/run_demo_worker.sh
```

```bash
.venv/bin/pytest -q tests/demo/test_seed.py tests/api/test_entities.py tests/api/test_web_ui.py tests/api/test_sync_jobs.py
```

### Tests Run

- `.venv/bin/ruff check app/demo tests/demo/test_seed.py tests/test_support.py`
- `sh -n scripts/reset_seeded_demo_env.sh`
- `sh -n scripts/run_demo_worker.sh`
- `.venv/bin/pytest -q tests/demo/test_seed.py tests/api/test_entities.py tests/api/test_web_ui.py tests/api/test_sync_jobs.py`

### Acceptance Result

- reusable synthetic demo seed data now lives outside test-only helpers
- `.venv/bin/python -m app.demo.seed` exists and prints only safe deterministic IDs
- `./scripts/reset_seeded_demo_env.sh` exists and seeds fixed artist/release/track/job identifiers
- `./scripts/run_demo_worker.sh` exists and mirrors the demo API environment
- targeted seed coverage is green with `28 passed`

### Prompt For The Next Milestone

`Реализуй Milestone 3 Stage 1: прогони ./scripts/reset_seeded_demo_env.sh и DEMO_LOAD_DOTENV=0 ./scripts/run_demo_api.sh, затем зафиксируй exact status codes и observed payload facts для seeded detail/job/UI routes и blank-token /search в docs/artifacts/exact_branch_verification_2026_03_20.md.`

## Milestone 3: Staging-Like Exact Verification

### Changed Files

- `docs/artifacts/exact_branch_verification_2026_03_20.md`
- `docs/artifacts/walkthrough_release_hardening_stage_1.md`
- `docs/artifacts/project_stage_status.md`

### Commands Run

```bash
./scripts/reset_seeded_demo_env.sh
```

```bash
DEMO_LOAD_DOTENV=0 ./scripts/run_demo_api.sh
```

```bash
curl -i http://127.0.0.1:8001/health
```

```bash
curl -i http://127.0.0.1:8001/artists/910001
curl -i http://127.0.0.1:8001/releases/920001
curl -i http://127.0.0.1:8001/tracks/930001
curl -i http://127.0.0.1:8001/jobs/00000000-0000-4000-8000-000000910001
```

```bash
curl -i http://127.0.0.1:8001/ui/artists/910001
curl -i http://127.0.0.1:8001/ui/releases/920001
curl -i http://127.0.0.1:8001/ui/tracks/930001
curl -i http://127.0.0.1:8001/ui/jobs/00000000-0000-4000-8000-000000910001
```

```bash
curl -i 'http://127.0.0.1:8001/search?q=Motorama&kind=artist&limit=5'
```

### Tests Run

- seeded runtime probes only

### Acceptance Result

- seeded detail and job routes returned `200` on the blank-token staging-like run
- seeded UI artist/release/track/job pages returned `200`
- blank-token `Motorama` search still returned `200` with `cache.status="miss"` because public Yandex search remained available
- the exact branch verification artifact now captures the real seeded staging-like route results for the current SHA

### Prompt For The Next Milestone

`Реализуй Milestone 4 Stage 1: подними live production-like path на exact branch, запусти ./scripts/run_demo_worker.sh рядом с API, materialize Krovostok и Motorama через live search/UI, затем POST /sync/artist/{artist_id}, poll /jobs/{job_id} до terminal state и зафиксируй exact outcomes в exact_branch_verification_2026_03_20.md и production_like_verification.md.`

## Milestone 4: Worker/Sync Readiness On The Exact Branch

### Changed Files

- `docs/artifacts/exact_branch_verification_2026_03_20.md`
- `docs/artifacts/production_like_verification.md`
- `docs/artifacts/project_stage_status.md`
- `docs/artifacts/walkthrough_release_hardening_stage_1.md`

### Commands Run

```bash
.venv/bin/ruff check .
```

```bash
.venv/bin/pytest -q
```

```bash
./scripts/reset_demo_env.sh
```

```bash
./scripts/run_demo_api.sh
```

```bash
./scripts/run_demo_worker.sh
```

```bash
curl -i http://127.0.0.1:8001/health
```

```bash
curl -i 'http://127.0.0.1:8001/search?q=Krovostok&kind=artist&limit=5'
curl -i -X POST http://127.0.0.1:8001/sync/artist/4
curl -i http://127.0.0.1:8001/jobs/b59ab5f2-c3f6-4a63-aeb5-500e2acc696e
curl -i http://127.0.0.1:8001/artists/4
curl -i http://127.0.0.1:8001/ui/artists/4
```

```bash
curl -i 'http://127.0.0.1:8001/search?q=Motorama&kind=artist&limit=5'
curl -i -X POST http://127.0.0.1:8001/sync/artist/2
curl -i http://127.0.0.1:8001/jobs/0a8eb713-e1dc-4885-8a5d-83c8a576c2d4
curl -i http://127.0.0.1:8001/artists/2
curl -i http://127.0.0.1:8001/ui/artists/2
```

### Tests Run

- `.venv/bin/ruff check .`
- `.venv/bin/pytest -q`
- live production-like probes for `Krovostok` and `Motorama`

### Acceptance Result

- full local baseline stayed green with `118 passed in 5.26s`
- live `Krovostok` search -> sync -> job -> artist/ui verification passed on the exact branch
- live `Motorama` search -> sync -> job -> artist/ui verification passed on the exact branch
- both terminal job payloads reached `finished`
- both terminal job payloads kept `partial=false`
- both artists kept `status="updated"` for YouTube and Yandex providers
- the exact branch verification artifact now contains both seeded staging-like and live production-like evidence for Stage 1 scope

### Prompt For The Next Milestone

`Реализуй Stage 2 deployability: добавь reproducible application Docker image для FastAPI web/api и RQ worker, затем добавь Render staging deployment automation от exact verified branch, не расширяя scope в public internet access, TLS termination или app-level auth.`
