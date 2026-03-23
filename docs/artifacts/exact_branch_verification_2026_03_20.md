# Exact Branch Verification: `0e911d2fd123e472b2aa661fd06a8f2fac009747`

Status: passed on `2026-03-23`.

## Scope

- exact branch SHA: `0e911d2fd123e472b2aa661fd06a8f2fac009747`
- branch: `yandex-catalog-ingest-pr`
- this artifact replaces stale dirty-worktree language with exact dated evidence
- Stage 1 verification boundary:
  - deterministic blank-token seeded demo path
  - exact live worker/sync re-verification for `Krovostok` and `Motorama`

## Frozen Branch Snapshot

These commands were the Stage 1 starting-point snapshot for the clean branch tip on `2026-03-20`.

### Commands Actually Run

```bash
git status -sb
```

```bash
git rev-parse HEAD
```

```bash
git diff --stat $(git merge-base HEAD main)..HEAD
```

```bash
.venv/bin/ruff check .
```

```bash
.venv/bin/pytest -q
```

### Exact Observations

- worktree was clean on `yandex-catalog-ingest-pr`
- exact SHA was `0e911d2fd123e472b2aa661fd06a8f2fac009747`
- branch diff versus `main` remained large and multi-subsystem
- `.venv/bin/ruff check .` passed
- `.venv/bin/pytest -q` passed with `115 passed in 3.58s`

## Post-Implementation Local Baseline

These commands were re-run after the Stage 1 implementation diff was applied locally on `2026-03-23`.

### Commands Actually Run

```bash
.venv/bin/ruff check .
```

```bash
.venv/bin/pytest -q
```

### Exact Observations

- `.venv/bin/ruff check .` passed
- `.venv/bin/pytest -q` passed with `118 passed in 5.26s`
- the extra passing tests came from Stage 1 seeded demo coverage, not from a widened live-claim boundary

## Staging-Like Seeded Verification

Status: passed on `2026-03-23` for the blank-token deterministic demo path.

### Commands Actually Run

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
```

```bash
curl -i http://127.0.0.1:8001/releases/920001
```

```bash
curl -i http://127.0.0.1:8001/tracks/930001
```

```bash
curl -i http://127.0.0.1:8001/jobs/00000000-0000-4000-8000-000000910001
```

```bash
curl -i http://127.0.0.1:8001/ui/artists/910001
```

```bash
curl -i http://127.0.0.1:8001/ui/releases/920001
```

```bash
curl -i http://127.0.0.1:8001/ui/tracks/930001
```

```bash
curl -i http://127.0.0.1:8001/ui/jobs/00000000-0000-4000-8000-000000910001
```

```bash
curl -i 'http://127.0.0.1:8001/search?q=Motorama&kind=artist&limit=5'
```

### Exact Observations

- `./scripts/reset_seeded_demo_env.sh` finished successfully and printed the deterministic IDs:
  - `artist_id=910001`
  - `release_id=920001`
  - `track_id=930001`
  - `job_id=00000000-0000-4000-8000-000000910001`
- `GET /health` returned `200` with `status=ok`, `database.status=ok`, and `redis.status=ok`
- `GET /artists/910001` returned `200`
  - both seeded platform links were present
  - `yandex_catalog_sections` was non-empty
  - `missing_on_yandex_view.total_items=3`
- `GET /releases/920001` returned `200`
  - release remained intentionally partial with `missing_platforms=["yandex"]`
- `GET /tracks/930001` returned `200`
  - both seeded platform links were present
- `GET /jobs/00000000-0000-4000-8000-000000910001` returned `200`
  - `status="finished"`
  - `partial=false`
  - both seeded providers were `status="updated"`
- `GET /ui/artists/910001` returned `200`
  - rendered `Что есть в каталоге Yandex`
  - rendered `Нет на Yandex`
  - rendered related release and track links
- `GET /ui/releases/920001` returned `200`
- `GET /ui/tracks/930001` returned `200`
- `GET /ui/jobs/00000000-0000-4000-8000-000000910001` returned `200`
  - rendered `Карточка обновлена.`
- blank-token `GET /search?q=Motorama&kind=artist&limit=5` returned `200`
  - `cache.status="miss"`
  - top `canonical_id=2`
  - response remained available because public Yandex search was still usable in the current provider wiring

### Claim Boundary

- the seeded detail/job/UI path is now stable and deterministic on the exact branch tip
- this proves a staging-like demo path that does not depend on fresh lookup luck
- this does not prove generalized blank-token `/search` behavior across environments

## Production-Like Worker/Sync Verification

Status: passed on `2026-03-23`.

### Commands Actually Run

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
```

```bash
curl -i -X POST http://127.0.0.1:8001/sync/artist/4
```

```bash
curl -i http://127.0.0.1:8001/jobs/b59ab5f2-c3f6-4a63-aeb5-500e2acc696e
```

```bash
curl -i http://127.0.0.1:8001/artists/4
```

```bash
curl -i http://127.0.0.1:8001/ui/artists/4
```

```bash
curl -i 'http://127.0.0.1:8001/search?q=Motorama&kind=artist&limit=5'
```

```bash
curl -i -X POST http://127.0.0.1:8001/sync/artist/2
```

```bash
curl -i http://127.0.0.1:8001/jobs/0a8eb713-e1dc-4885-8a5d-83c8a576c2d4
```

```bash
curl -i http://127.0.0.1:8001/artists/2
```

```bash
curl -i http://127.0.0.1:8001/ui/artists/2
```

### Exact Observations

- `GET /health` returned `200` before the live sync run

#### Krovostok

- live `GET /search?q=Krovostok&kind=artist&limit=5` returned `200`
  - `cache.status="fresh"`
  - top `canonical_id=4`
  - top provider IDs:
    - YouTube `UCi-dSgoZzJRuV5AWDkQi9zA`
    - Yandex `218095`
- `POST /sync/artist/4` returned `202`
- job `b59ab5f2-c3f6-4a63-aeb5-500e2acc696e` reached terminal state with `GET /jobs/... = 200`
  - `status="finished"`
  - `partial=false`
  - providers:
    - YouTube `status="updated"`, `mode="entity_refresh"`, `attempts=1`
    - Yandex `status="updated"`, `mode="catalog_ingest"`, `attempts=1`, `catalog_artist_provider_id="218095"`, `platform_artist_count=12`, `platform_release_count=15`, `platform_track_count=147`, `catalog_list_count=10`
- post-sync `GET /artists/4` returned `200`
  - `yandex_catalog_sections` count remained `2`
  - `missing_on_yandex_view.total_items=0`
- post-sync `GET /ui/artists/4` returned `200`
  - rendered `Что есть в каталоге Yandex`
  - rendered `Нет на Yandex`

#### Motorama

- live `GET /search?q=Motorama&kind=artist&limit=5` returned `200`
  - `cache.status="stale"`
  - top `canonical_id=2`
  - top provider IDs:
    - YouTube `UC9Vtn5WRFoHdkb5fbXswmWw`
    - Yandex `2813376`
- `POST /sync/artist/2` returned `202`
- job `0a8eb713-e1dc-4885-8a5d-83c8a576c2d4` reached terminal state with `GET /jobs/... = 200`
  - `status="finished"`
  - `partial=false`
  - providers:
    - YouTube `status="updated"`, `mode="entity_refresh"`, `attempts=1`
    - Yandex `status="updated"`, `mode="catalog_ingest"`, `attempts=1`, `catalog_artist_provider_id="2813376"`, `platform_artist_count=2`, `platform_release_count=1`, `platform_track_count=1`, `catalog_list_count=10`
- post-sync `GET /artists/2` returned `200`
  - `yandex_catalog_sections` count remained `2`
  - `missing_on_yandex_view.total_items=0`
- post-sync `GET /ui/artists/2` returned `200`
  - rendered `Что есть в каталоге Yandex`
  - rendered `Нет на Yandex`

### Claim Boundary

- safe: exact-query live search plus worker-backed refresh certification for `Krovostok` and `Motorama` on `2026-03-23`
- safe: post-sync artist overview rendering remained intact for those exact certified artists
- not safe: generalized live-provider reliability claims beyond those exact artists or beyond artist sync

## Stage 1 Exit

Stage 1 is complete for the intended scope:

- exact branch freeze evidence exists for `0e911d2fd123e472b2aa661fd06a8f2fac009747`
- deterministic seeded demo IDs now exist for blank-token staging-like demos
- seeded staging-like detail/job/UI verification is preserved with exact commands and exact outcomes
- production-like worker/sync verification is preserved for `Krovostok` and `Motorama`
- deploy workflow, Docker image build path, and public access layer remain explicitly out of scope and unresolved
