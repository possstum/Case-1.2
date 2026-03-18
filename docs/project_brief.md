# Project Brief: НЕТвРФ

Короткая заметка: этот brief описывает текущую branch-state репозитория после Yandex catalog expansion по фактическому коду и latest verification snapshot на `2026-03-19`. При конфликте между runtime, brief и README приоритет у того, что реально подключено в `app/main.py`, затем у этого brief, затем у high-level runbook в `README.md`.

## 1. Краткое назначение проекта и что считается MVP сейчас

Статус: audited against current code and verified docs baseline.

### Назначение

Проект предназначен для поиска и сопоставления музыкальных сущностей между YouTube Music и Yandex Music, с canonical-слоем, explainability и фоновыми sync jobs.

### Текущая стадия проекта

По состоянию на `2026-03-19` текущая стадия проекта формулируется как `expanded MVP with active integration and stabilization`. Этот label означает, что проект уже заметно шире health-only scaffold: API и web UI смонтированы, detail/search/sync flows реализованы, а Yandex catalog expansion уже подключен в ветке. При этом это еще не production-ready label, потому что live-provider readiness остается частично непроверенной, хотя локальный verification baseline этой ветки уже снова зеленый.

### Текущий MVP

Текущий MVP уже шире старого health-only baseline. В живом `FastAPI` приложении смонтированы и доступны:

- API routes: `/health`, `/search`, `/artists/{artist_id}`, `/releases/{release_id}`, `/tracks/{track_id}`, `/sync/{kind}/{target_id}`, `/jobs/{job_id}`
- Web UI routes: `/`, `/ui`, `/ui/artists/{artist_id}`, `/ui/releases/{release_id}`, `/ui/tracks/{track_id}`, `/ui/sync/{kind}/{target_id}`, `/ui/jobs/{job_id}`
- единая ошибка `{"error": ...}`
- correlation-id middleware
- JSON logging с redaction
- SQLite WAL dev mode
- staging-like host-run baseline against PostgreSQL + Redis
- Yandex catalog ingestion and segmented provider-side storage

### Что входит в verified baseline

- `GET /health` success path
- mounted-route presence for API surface above
- rate-limited behavior for `/search`
- `404 not_found` behavior for missing detail IDs
- `/ui` availability, включая empty-results state и provider-disabled fallback when the effective provider registry is empty
- staging-like `/health`, `/search`, and `/ui` success with PostgreSQL + Redis and blank provider tokens under the current default wiring

### Что не входит в verified baseline

- live provider search behavior with real `YOUTUBE_MUSIC_TOKEN` / `YANDEX_MUSIC_TOKEN`
- fully verified live refresh behavior through worker and provider HTTP
- fully verified YouTube detail refresh behavior via `get_artist`, `get_release`, and `get_track`
- любые claims о production readiness beyond the verified local and staging-like baseline

## 2. Актуальное дерево репозитория по подсистемам

Статус: audited against current code.

```text
app/
  main.py                  FastAPI app factory; mounts web and API routers
  api/
    router.py              includes health, search, entity detail, sync, and jobs routers
    routes/                route modules for health, search, entities, sync, jobs
    schemas/               Pydantic API contracts
    deps.py                DB/Redis/provider/service/rate-limit dependency factories
  core/                    config, logging, middleware, exception handling
  db/                      SQLAlchemy models, repositories, session/bootstrap helpers
  providers/               provider contracts, registry, HTTP clients, payload schemas, mappers
  services/                health, search, detail, link, matching, sync, and Yandex catalog ingestion services
  tasks/                   RQ queue helpers, worker entrypoint, sync job runner, search refresh stub
  web/                     HTML routes, renderers, static assets
scripts/
  run_api.sh               uvicorn launcher with optional reload toggle
  run_worker.sh            RQ worker launcher
alembic/
  env.py                   Alembic environment wired to Base.metadata
  versions/                schema revisions used by the verified local/staging-like baseline
docs/
  project_brief.md
  artifacts/*
data/
  local SQLite files
```

## 3. Где находится backend, web UI, worker и queue

Статус: audited against current code.

| Подсистема | Основные файлы | Runtime status | Статус |
| --- | --- | --- | --- |
| Backend API | `app/main.py`, `app/api/router.py`, `app/api/routes/*` | реально смонтирован и обслуживает health/search/detail/sync/job routes | live |
| Web UI | `app/web/routes.py`, `app/web/render.py`, `app/web/static/*` | реально смонтирован через `web_router` | live |
| Worker | `app/tasks/worker.py`, `scripts/run_worker.sh` | запускается как отдельный RQ worker process | partial |
| Queue layer | `app/tasks/queue.py` | создает Redis connection, queue lookup и enqueue для sync jobs | partial |

## 4. Точки входа

Статус: audited against current code.

| Entry point | File or module | Как запускается | Что подключает | Статус |
| --- | --- | --- | --- | --- |
| app startup | `app/main.py:create_app` | `./scripts/run_api.sh` or `uvicorn app.main:create_app --factory` | middleware, exception handlers, static files, `web_router`, `api_router` | live |
| API router | `app/api/router.py:api_router` | через `application.include_router(...)` | health, search, entities, sync, jobs | live |
| web UI router | `app/web/routes.py:web_router` | через `application.include_router(web_router)` | `/`, `/ui`, entity pages, sync redirect, job page | live |
| worker entrypoint | `app/tasks/worker.py:main` | `./scripts/run_worker.sh` or `python -m app.tasks.worker` | RQ worker on configured queues | partial |

## 5. Таблица реальных endpoint-ов

Статус: audited against current code and verified docs baseline.

| Method | Path | Handler | Verified baseline note | Статус |
| --- | --- | --- | --- | --- |
| GET | `/health` | `app.api.routes.health.get_health` | `200` success path verified locally and in staging-like mode | live / verified |
| GET | `/search` | `app.api.routes.search.search` | mounted; rate limiting is verified; cold-miss `503` remains supported when the effective provider registry is empty, but current branch wiring usually searches Yandex even with blank `YANDEX_MUSIC_TOKEN` | live / partial verification |
| GET | `/artists/{artist_id}` | `app.api.routes.artists.get_artist` | mounted; missing-ID `404` verified; `200` success path requires existing canonical rows | live / partial verification |
| GET | `/releases/{release_id}` | `app.api.routes.releases.get_release` | mounted; missing-ID `404` verified; `200` success path requires existing canonical rows | live / partial verification |
| GET | `/tracks/{track_id}` | `app.api.routes.tracks.get_track` | mounted; missing-ID `404` verified; `200` success path requires existing canonical rows | live / partial verification |
| POST | `/sync/{kind}/{target_id}` | `app.api.routes.sync.enqueue_sync` | mounted; `429` path verified; `202` supported when target exists and queueing succeeds; no live refresh claims | live / partial verification |
| GET | `/jobs/{job_id}` | `app.api.routes.jobs.get_job` | mounted; `200` for existing jobs and `404` for unknown IDs are part of supported behavior | live |
| GET | `/` | `app.web.routes.root_redirect` | redirects to `/ui` | live |
| GET | `/ui` | `app.web.routes.ui_search` | landing page works; cold misses may render either a provider-disabled notice or a normal empty-results page depending on the effective provider registry | live / partial verification |
| GET | `/ui/artists/{artist_id}` | `app.web.routes.ui_artist` | renders existing canonical artist detail rows | live |
| GET | `/ui/releases/{release_id}` | `app.web.routes.ui_release` | renders existing canonical release detail rows | live |
| GET | `/ui/tracks/{track_id}` | `app.web.routes.ui_track` | renders existing canonical track detail rows | live |
| POST | `/ui/sync/{kind}/{target_id}` | `app.web.routes.ui_sync` | redirects to `/ui/jobs/{job_id}` when enqueue succeeds | live / partial verification |
| GET | `/ui/jobs/{job_id}` | `app.web.routes.ui_job` | renders stored sync job status | live |

## 6. Таблица моделей БД

Статус: audited against ORM definitions and verified baseline tables.

Короткая заметка: staging-like verification явно проверяла наличие `artists`, `search_cache`, и `sync_jobs`. Таблица ниже описывает ORM inventory, на который опираются runtime services и repositories.

| Model | Таблица | Назначение |
| --- | --- | --- |
| `Artist` | `artists` | canonical artist |
| `ArtistAlias` | `artist_aliases` | alias artist-а |
| `Release` | `releases` | canonical release |
| `Track` | `tracks` | canonical track |
| `ReleaseArtist` | `release_artists` | release credits |
| `TrackArtist` | `track_artists` | track credits |
| `ReleaseTrack` | `release_tracks` | canonical tracklist |
| `PlatformArtist` | `platform_artists` | provider artist snapshot |
| `PlatformRelease` | `platform_releases` | provider release snapshot |
| `PlatformTrack` | `platform_tracks` | provider track snapshot |
| `PlatformReleaseTrack` | `platform_release_tracks` | provider tracklist |
| `LinkArtist` | `links_artist` | canonical artist to provider artist link |
| `LinkRelease` | `links_release` | canonical release to provider release link |
| `LinkTrack` | `links_track` | canonical track to provider track link |
| `SearchCache` | `search_cache` | cached search response |
| `SyncJob` | `sync_jobs` | queued / running / finished / failed sync job |

## 7. Таблица сервисов

Статус: audited against current code.

| Сервис | Что делает | Runtime role today | Ограничения | Статус |
| --- | --- | --- | --- | --- |
| `HealthService` | проверка app/database/redis | live `/health` | зависит от configured DB/Redis | fully implemented |
| `ArtistService` | artist detail with aliases, credits, platform links | live detail routes | success path requires existing canonical data | implemented |
| `ReleaseService` | release detail with artists/tracks/platforms | live detail routes | success path requires existing canonical data | implemented |
| `TrackService` | track detail with artists/releases/platforms | live detail routes | success path requires existing canonical data | implemented |
| `LinkService` | persist canonical/platform/link rows | used by search and sync flows | relies on provider/entity inputs | implemented |
| `MatchingService` | matching and explainability scoring | used by search flow | live provider quality not verified | implemented |
| `SearchService` | cache-first search, provider fan-out, stale handling | live `/search` and cache-backed `/ui` | no-provider degraded path verified; live provider results not fully verified | implemented / partially verified |
| `SyncService` | enqueue jobs, read job state, execute refresh | live `/sync` and `/jobs`; worker execution path exists | live provider refresh success not verified | implemented / partially verified |
| `YandexCatalogIngestionService` | ingests Yandex artist/release/track graphs and segmented provider catalog lists | used by Yandex-linked sync execution | live provider HTTP and end-to-end sync readiness are still only partially verified | implemented / partially verified |

## 8. Таблица provider layer

Статус: audited against current code.

| Интерфейс / компонент | Реальные реализации | Verified baseline note | Статус |
| --- | --- | --- | --- |
| `MusicProvider` contract | `app.providers.base.MusicProvider` | contract and test doubles are in place | fully implemented contract |
| `ProviderRegistry` | `app.providers.registry.ProviderRegistry` | runtime lookup/iteration works | fully implemented |
| `YouTubeMusicClient.search()` | concrete HTTP search client | code exists, but live-token behavior is not verified for baseline claims | partial / unverified live behavior |
| `YandexMusicClient.search()` | concrete HTTP search client | code exists, but live-token behavior is not verified for baseline claims | partial / unverified live behavior |
| `YouTubeMusicClient.get_*()` | concrete methods present | all detail refresh methods still raise `NotImplementedError` | stub |
| `YandexMusicClient.get_*()` | concrete detail fetch methods | used by Yandex catalog ingestion and sync refresh wiring; live behavior is still only partially verified | implemented / partially verified live behavior |
| YouTube mapper layer | `map_artist`, `map_release`, `map_track` | mapper layer is implemented and tested | implemented |
| Yandex mapper layer | `map_artist`, `map_release`, `map_track` | mapper layer is implemented and tested | implemented |

## 9. Пошаговые runtime flow

Статус: audited against current code.

### Search Flow

1. `GET /search` is mounted in `app/api/router.py`.
2. Request goes through Redis-backed search rate limiting.
3. `SearchService.search()` checks `search_cache` first.
4. Fresh or stale cache hits return `200` even when providers are unavailable.
5. Cold miss or expired cache returns `503 search_providers_unavailable` only when the effective provider registry is empty.
6. In the current branch default wiring, public Yandex search keeps one usable provider available even when `YANDEX_MUSIC_TOKEN` is blank, so a cold miss may return a normal `200` search page with empty results instead of a provider-disabled fallback.
7. When providers are configured, code fans out across provider clients and persists merged results, but that live-provider success path is not part of the fully verified baseline.

### Detail Flow

1. `GET /artists/{id}`, `/releases/{id}`, `/tracks/{id}` are mounted in runtime.
2. Services load canonical rows plus related aliases, credits, tracks, releases, and platform links.
3. Missing IDs return `404 not_found`.
4. `200` success paths require existing canonical rows in the active database.

### Sync Flow

1. `POST /sync/{kind}/{target_id}` is mounted in runtime.
2. Request goes through Redis-backed sync rate limiting.
3. `SyncService.enqueue()` validates the target, reuses an active job when possible, or creates a new `sync_jobs` row.
4. `RQSyncJobScheduler` enqueues `app.tasks.sync_jobs.run_sync_job` into Redis-backed RQ.
5. Returning `202` only means queueing succeeded; it does not prove that live provider refresh was successful.

### Jobs Flow

1. `GET /jobs/{job_id}` returns stored sync job state.
2. Existing jobs may be `queued`, `running`, `finished`, or `failed`.
3. Unknown IDs return `404 not_found`.
4. Worker execution exists, but successful live provider refresh is not a verified baseline claim because only parts of provider refresh have been exercised end-to-end and YouTube detail refresh still remains stubbed.

## 10. Что реально делает queue / worker

Статус: audited against current code.

| Компонент | Что реально происходит | Ограничения | Статус |
| --- | --- | --- | --- |
| `app/tasks/queue.py` | создает Redis connection, `Queue(name)` и enqueue для sync jobs | Redis must be reachable | implemented |
| `app/tasks/worker.py` | поднимает стандартный RQ worker | отдельный процесс, не часть `run_api.sh` | implemented |
| `app/tasks/sync_jobs.run_sync_job` | открывает DB session, строит `SyncService`, запускает `execute(job_id)` | упирается в unverified provider refresh path | partial |
| `app/tasks/search_jobs.refresh_search_cache` | search refresh worker path | implementation remains stubbed | stub |

## 11. Список env-переменных и какие из них обязательны

Статус: audited against `app/core/config.py`.

Короткая заметка: `Settings` now includes app, DB, Redis, matching, search, sync, rate-limit, and provider-token fields. Формально все env имеют defaults, но функционально есть разные режимы работы.

| Env group | Примеры | Роль в baseline | Примечание |
| --- | --- | --- | --- |
| app | `APP_ENV`, `APP_DEBUG`, `APP_HOST`, `APP_PORT`, `APP_RELOAD` | startup/runtime mode | `.env.example` and `.env.staging.example` already cover this |
| database | `DATABASE_URL`, `SQL_ECHO` | SQLite dev or PostgreSQL staging-like | dev default is SQLite WAL |
| redis/rq | `REDIS_URL`, `RQ_DEFAULT_QUEUE`, `HEALTH_REQUIRE_REDIS` | rate limits, queueing, health | staging-like baseline sets Redis required |
| matching/search/sync policy | `MATCH_*`, `SEARCH_*`, `SYNC_*`, `PROVIDER_HTTP_TIMEOUT_SECONDS` | search, sync, retry, cache behavior | all declared in `Settings` |
| provider tokens | `YOUTUBE_MUSIC_TOKEN`, `YANDEX_MUSIC_TOKEN` | optional live provider fan-out | YouTube requires a token; current branch Yandex public search may still work with a blank token, but blank tokens still reduce verified live behavior |

## 12. Как поднять проект локально

Статус: aligned to the verified README runbook.

### Минимальный dev сценарий

1. `python3 -m venv .venv`
2. `.venv/bin/python -m pip install -e '.[dev]'`
3. `cp .env.example .env`
4. `mkdir -p data`
5. `.venv/bin/alembic upgrade head`
6. `./scripts/run_api.sh`

### Staging-like сценарий

1. `.venv/bin/python -m pip install -e '.[dev]'`
2. `cp .env.staging.example .env.staging`
3. `docker compose up -d postgres redis`
4. дождаться `pg_isready` и `redis-cli ping`
5. `set -a; . ./.env.staging; set +a`
6. `.venv/bin/alembic upgrade head`
7. `./scripts/run_api.sh`

### Важные caveats

- blank provider tokens no longer imply an empty provider registry in the current branch default wiring
- `/search` may still return `200` from public Yandex search in that mode; `503 search_providers_unavailable` is expected only when the effective provider registry is empty
- detail success paths depend on existing canonical rows
- live provider execution is not part of the supported baseline story

## 13. Какие тесты есть и что они реально покрывают

Статус: aligned to the current branch verification snapshot and older runtime verification artifacts.

| Test suite or file | Что реально покрывает | Current note |
| --- | --- | --- |
| `tests/api/test_health.py` | `/health` response shape | part of the passing local baseline |
| `tests/api/test_search.py` | cache, degraded no-provider behavior, rate limits, retries | part of the passing local baseline |
| `tests/api/test_entities.py` | detail response shape and missing-ID `404` | part of the passing local baseline |
| `tests/api/test_sync_jobs.py` | sync enqueue and job status API behavior | part of the passing local baseline |
| `tests/api/test_web_ui.py` | `/`, `/ui`, notice fallback, entity/job pages, and empty-kind normalization expectations | part of the passing local baseline |
| `tests/services/*` | matching and sync service behavior | part of the passing local baseline |
| `tests/providers/*` | provider contracts and mappers | part of the passing local baseline |
| `tests/db/*`, `tests/core/*`, `tests/utils/*` | DB, logging, normalization, helpers | part of the passing local baseline |

Current local verification snapshot on `2026-03-19`:

- `.venv/bin/python -m ruff check .` passed
- `.venv/bin/python -m pytest -q tests/api` passed with `31 passed`
- `.venv/bin/python -m pytest -q tests/services tests/providers tests/db tests/utils tests/core` passed with `42 passed`
- `.venv/bin/python -m pytest -q` passed with `73 passed`

## 14. Статус реализации

Статус: audited against current code and verified docs baseline.

### Fully Implemented Or Live In Runtime

- FastAPI app factory, middleware, exception envelope, JSON logging with redaction
- mounted API routers for health, search, detail, sync, and jobs
- mounted web UI router
- DB/bootstrap/config/rate-limit dependency factories
- SQLAlchemy models, repositories, and detail services
- Redis queue helper and worker launcher
- Yandex catalog ingestion and segmented provider storage wiring

### Partially Verified For Baseline

- `SearchService` live provider fan-out path
- `SyncService.execute()` live provider refresh path
- web UI success paths that require pre-existing canonical data
- queue-backed sync execution beyond enqueue/job-status semantics
- Yandex live provider behavior beyond the current branch snapshot

### Stub / Placeholder

- provider detail refresh methods `YouTubeMusicClient.get_*()`
- `app/tasks/search_jobs.refresh_search_cache`

## 15. Что реально подключено в runtime versus что пока ограничено baseline

Статус: audited against current code.

| Компонент | Подключен в runtime | Ограничение baseline |
| --- | --- | --- |
| Health API | да | verified success path |
| Search API | да | rate limiting is verified; `503 search_providers_unavailable` now depends on an effectively empty provider registry, while default branch wiring usually still has Yandex search |
| Entity detail API | да | success path requires existing canonical data |
| Sync API | да | enqueue/status supported; live provider refresh unverified |
| Jobs API | да | depends on existing jobs |
| Web UI | да | empty-results HTML is current branch baseline; provider-disabled notice is only a fallback when the effective provider registry is empty |
| Worker process | отдельно запускается | not required for the docs-only baseline |
| Search refresh job | code path exists | worker implementation remains stubbed |
| Live provider refresh | limited | YouTube `get_*()` remains unimplemented, and broader end-to-end live refresh is still not fully verified |

## 16. Расхождения между старой документацией и текущим кодом

Статус: resolved by this docs alignment pass.

- Старый README описывал репозиторий как foundation skeleton с одним `/health`; это больше не соответствует текущему runtime wiring.
- Старый brief описывал search/detail/sync/jobs/web как dormant or not wired; сейчас они реально смонтированы.
- Current baseline story is now standardized around verified local and staging-like behavior, including acceptable degraded states.
- Документация больше не обещает live provider behavior, который не был отдельно подтвержден.
