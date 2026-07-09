#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:5024}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3000}"

echo "=== Vehicle Tracker Health Check ==="

check() {
  local name="$1"
  local url="$2"
  if curl -sf "$url" > /dev/null; then
    echo "[OK] $name — $url"
  else
    echo "[FAIL] $name — $url"
    return 1
  fi
}

check "Backend" "$BACKEND_URL/health"
check "Gateway" "$GATEWAY_URL/health"
check "Frontend" "$FRONTEND_URL/api/health"

echo "=== All services healthy ==="
