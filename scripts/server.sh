#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-help}" in
  init) python3 scripts/server_check.py --init ;;
  check) python3 scripts/server_check.py "${2:-process}" ;;
  build) docker compose build processor ;;
  run)
    python3 scripts/server_check.py process
    docker compose run --rm processor
    ;;
  up)
    python3 scripts/server_check.py web
    docker compose up -d --wait --wait-timeout 60 web
    ;;
  status) docker compose ps ;;
  logs) docker compose logs --tail 100 -f web ;;
  stop) docker compose stop web ;;
  *)
    echo 'Usage: scripts/server.sh init|check [process|web]|build|run|up|status|logs|stop'
    ;;
esac
