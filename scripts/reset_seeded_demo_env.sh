#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

if [ -x "$ROOT_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
else
  PYTHON_BIN="python3"
fi

DEMO_DB_HOST="${DEMO_DB_HOST:-127.0.0.1}"
DEMO_DB_PORT="${DEMO_DB_PORT:-5433}"
DEMO_DB_NAME="${DEMO_DB_NAME:-netvrf}"
DEMO_DB_USER="${DEMO_DB_USER:-netvrf}"
DEMO_DB_PASSWORD="${DEMO_DB_PASSWORD:-netvrf}"
DEMO_REDIS_HOST="${DEMO_REDIS_HOST:-127.0.0.1}"
DEMO_REDIS_PORT="${DEMO_REDIS_PORT:-6380}"
DEMO_REDIS_DB="${DEMO_REDIS_DB:-0}"

DATABASE_URL="postgresql+psycopg://${DEMO_DB_USER}:${DEMO_DB_PASSWORD}@${DEMO_DB_HOST}:${DEMO_DB_PORT}/${DEMO_DB_NAME}"
REDIS_URL="redis://${DEMO_REDIS_HOST}:${DEMO_REDIS_PORT}/${DEMO_REDIS_DB}"

"$ROOT_DIR/scripts/reset_demo_env.sh"

echo "Seeding deterministic demo rows..."
exec env \
  APP_ENV=staging \
  APP_DEBUG=false \
  APP_RELOAD=false \
  HEALTH_REQUIRE_REDIS=true \
  DATABASE_URL="$DATABASE_URL" \
  REDIS_URL="$REDIS_URL" \
  PYTHONUNBUFFERED=1 \
  "$PYTHON_BIN" -m app.demo.seed
