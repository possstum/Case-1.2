#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

ENV_FILE="${DEMO_ENV_FILE:-$ROOT_DIR/.env}"
DEMO_LOAD_DOTENV="${DEMO_LOAD_DOTENV:-1}"

if [ "$DEMO_LOAD_DOTENV" = "1" ] && [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
fi

DEMO_DB_HOST="${DEMO_DB_HOST:-127.0.0.1}"
DEMO_DB_PORT="${DEMO_DB_PORT:-5433}"
DEMO_DB_NAME="${DEMO_DB_NAME:-netvrf}"
DEMO_DB_USER="${DEMO_DB_USER:-netvrf}"
DEMO_DB_PASSWORD="${DEMO_DB_PASSWORD:-netvrf}"
DEMO_REDIS_HOST="${DEMO_REDIS_HOST:-127.0.0.1}"
DEMO_REDIS_PORT="${DEMO_REDIS_PORT:-6380}"
DEMO_REDIS_DB="${DEMO_REDIS_DB:-0}"
DEMO_APP_HOST="${DEMO_APP_HOST:-127.0.0.1}"
DEMO_APP_PORT="${DEMO_APP_PORT:-8001}"
DEMO_ACCESS_HOST="${DEMO_ACCESS_HOST:-}"
DEMO_PROVIDER_HTTP_TIMEOUT_SECONDS="${DEMO_PROVIDER_HTTP_TIMEOUT_SECONDS:-15}"
DEMO_SEARCH_PROVIDER_TIMEOUT_SECONDS="${DEMO_SEARCH_PROVIDER_TIMEOUT_SECONDS:-15}"
DEMO_SYNC_PROVIDER_TIMEOUT_SECONDS="${DEMO_SYNC_PROVIDER_TIMEOUT_SECONDS:-120}"

DATABASE_URL="postgresql+psycopg://${DEMO_DB_USER}:${DEMO_DB_PASSWORD}@${DEMO_DB_HOST}:${DEMO_DB_PORT}/${DEMO_DB_NAME}"
REDIS_URL="redis://${DEMO_REDIS_HOST}:${DEMO_REDIS_PORT}/${DEMO_REDIS_DB}"
BIND_UI_URL="http://${DEMO_APP_HOST}:${DEMO_APP_PORT}/ui"

is_loopback_host() {
  case "$1" in
    127.0.0.1 | localhost | ::1)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

echo "Starting demo API on ${BIND_UI_URL}"
if [ -n "$DEMO_ACCESS_HOST" ]; then
  echo "Share this URL with trusted private-network testers: http://${DEMO_ACCESS_HOST}:${DEMO_APP_PORT}/ui"
  if is_loopback_host "$DEMO_APP_HOST"; then
    echo "Warning: DEMO_ACCESS_HOST does not change the bind host. Set DEMO_APP_HOST=0.0.0.0 for LAN/VPN sharing." >&2
  fi
fi
if ! is_loopback_host "$DEMO_APP_HOST"; then
  echo "Trusted private network only: this shared path has no public-internet hardening, TLS, or auth layer."
fi
echo "Using isolated demo database and Redis."

exec env \
  APP_ENV=staging \
  APP_DEBUG=false \
  APP_RELOAD=false \
  APP_HOST="$DEMO_APP_HOST" \
  APP_PORT="$DEMO_APP_PORT" \
  HEALTH_REQUIRE_REDIS=true \
  DATABASE_URL="$DATABASE_URL" \
  REDIS_URL="$REDIS_URL" \
  PROVIDER_HTTP_TIMEOUT_SECONDS="$DEMO_PROVIDER_HTTP_TIMEOUT_SECONDS" \
  SEARCH_PROVIDER_TIMEOUT_SECONDS="$DEMO_SEARCH_PROVIDER_TIMEOUT_SECONDS" \
  SYNC_PROVIDER_TIMEOUT_SECONDS="$DEMO_SYNC_PROVIDER_TIMEOUT_SECONDS" \
  PYTHONUNBUFFERED=1 \
  "$ROOT_DIR/scripts/run_api.sh"
