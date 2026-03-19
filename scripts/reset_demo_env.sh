#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

if [ -x "$ROOT_DIR/.venv/bin/alembic" ]; then
  ALEMBIC_CMD="$ROOT_DIR/.venv/bin/alembic"
else
  ALEMBIC_CMD="$PYTHON_BIN -m alembic"
fi

DEMO_COMPOSE_PROJECT="${DEMO_COMPOSE_PROJECT:-netvrf-demo}"
DEMO_DB_HOST="${DEMO_DB_HOST:-127.0.0.1}"
DEMO_DB_PORT="${DEMO_DB_PORT:-5433}"
DEMO_DB_NAME="${DEMO_DB_NAME:-netvrf}"
DEMO_DB_USER="${DEMO_DB_USER:-netvrf}"
DEMO_DB_PASSWORD="${DEMO_DB_PASSWORD:-netvrf}"
DEMO_REDIS_HOST="${DEMO_REDIS_HOST:-127.0.0.1}"
DEMO_REDIS_PORT="${DEMO_REDIS_PORT:-6380}"
DEMO_REDIS_DB="${DEMO_REDIS_DB:-0}"
DEMO_WAIT_ATTEMPTS="${DEMO_WAIT_ATTEMPTS:-60}"

DEMO_DATABASE_URL="postgresql+psycopg://${DEMO_DB_USER}:${DEMO_DB_PASSWORD}@${DEMO_DB_HOST}:${DEMO_DB_PORT}/${DEMO_DB_NAME}"
DEMO_REDIS_URL="redis://${DEMO_REDIS_HOST}:${DEMO_REDIS_PORT}/${DEMO_REDIS_DB}"

OVERRIDE_FILE=$(mktemp "${TMPDIR:-/tmp}/netvrf-demo-compose.XXXXXX")

cleanup() {
  rm -f "$OVERRIDE_FILE"
}

trap cleanup EXIT INT TERM

cat > "$OVERRIDE_FILE" <<EOF
services:
  postgres:
    ports: !override
      - "${DEMO_DB_PORT}:5432"
  redis:
    ports: !override
      - "${DEMO_REDIS_PORT}:6379"
EOF

compose() {
  docker compose \
    -p "$DEMO_COMPOSE_PROJECT" \
    -f "$ROOT_DIR/docker-compose.yml" \
    -f "$OVERRIDE_FILE" \
    "$@"
}

wait_for_postgres() {
  attempt=1
  while [ "$attempt" -le "$DEMO_WAIT_ATTEMPTS" ]; do
    if compose exec -T postgres pg_isready -U "$DEMO_DB_USER" -d "$DEMO_DB_NAME" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    attempt=$((attempt + 1))
  done
  echo "Timed out waiting for PostgreSQL readiness." >&2
  return 1
}

wait_for_redis() {
  attempt=1
  while [ "$attempt" -le "$DEMO_WAIT_ATTEMPTS" ]; do
    if compose exec -T redis redis-cli ping >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    attempt=$((attempt + 1))
  done
  echo "Timed out waiting for Redis readiness." >&2
  return 1
}

echo "Resetting demo environment for compose project '$DEMO_COMPOSE_PROJECT'..."
compose down -v --remove-orphans >/dev/null 2>&1 || true
compose up -d postgres redis

wait_for_postgres
wait_for_redis

echo "Applying Alembic migrations to clean demo database..."
env \
  APP_ENV=staging \
  APP_DEBUG=false \
  APP_RELOAD=false \
  HEALTH_REQUIRE_REDIS=true \
  DATABASE_URL="$DEMO_DATABASE_URL" \
  REDIS_URL="$DEMO_REDIS_URL" \
  /bin/sh -c "cd \"$ROOT_DIR\" && exec $ALEMBIC_CMD upgrade head"

echo "Verifying clean table counts..."
compose exec -T postgres psql -U "$DEMO_DB_USER" -d "$DEMO_DB_NAME" -At -F '|' -c "
select 'artists', count(*) from artists
union all
select 'search_cache', count(*) from search_cache
union all
select 'sync_jobs', count(*) from sync_jobs
order by 1;
"

echo "Verifying Redis DB size..."
compose exec -T redis redis-cli -n "$DEMO_REDIS_DB" dbsize

echo "Demo environment ready."
echo "DATABASE_URL=$DEMO_DATABASE_URL"
echo "REDIS_URL=$DEMO_REDIS_URL"
echo "API_START=./scripts/run_demo_api.sh"
