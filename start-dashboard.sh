#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
FRONTEND_DIR="$ROOT_DIR/unified_control_dashboard/webapp/frontend"
FRONTEND_DIST_DIR="$FRONTEND_DIR/dist"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python bulunamadi: $PYTHON_BIN"
  echo "Once sanal ortami olusturup bagimliliklari kur." 
  exit 1
fi

export UI_HOST="${UI_HOST:-127.0.0.1}"
export UI_PORT="${UI_PORT:-8080}"

if [[ -d "$FRONTEND_DIR" ]]; then
  if [[ "${FORCE_FRONTEND_BUILD:-0}" == "1" || ! -d "$FRONTEND_DIST_DIR" ]]; then
    if command -v npm >/dev/null 2>&1; then
      echo "Vue frontend build aliniyor..."
      (
        cd "$FRONTEND_DIR"
        npm install
        npm run build
      )
    else
      echo "npm bulunamadi. Vue frontend build alinmadan devam ediliyor."
    fi
  fi
fi

cd "$ROOT_DIR/unified_control_dashboard"
echo "Backend + frontend baslatiliyor: http://$UI_HOST:$UI_PORT"
exec "$PYTHON_BIN" app.py



#lsof -ti tcp:8094 | xargs kill -9 2>/dev/null || true && UI_PORT=8094 FORCE_FRONTEND_BUILD=1 ./start-dashboard.sh