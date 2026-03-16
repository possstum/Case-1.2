#!/usr/bin/env sh
set -eu

if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
else
  PYTHON_BIN="python3"
fi

RELOAD_VALUE="${APP_RELOAD:-true}"

case "$RELOAD_VALUE" in
  0|false|FALSE|False|no|NO|No|off|OFF|Off)
    exec "$PYTHON_BIN" -m uvicorn app.main:create_app --factory --host "${APP_HOST:-127.0.0.1}" --port "${APP_PORT:-8000}"
    ;;
  *)
    exec "$PYTHON_BIN" -m uvicorn app.main:create_app --factory --host "${APP_HOST:-127.0.0.1}" --port "${APP_PORT:-8000}" --reload
    ;;
esac
