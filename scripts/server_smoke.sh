#!/usr/bin/env bash
# Requires an already built metro-guard:server image and Docker Compose.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p outputs
scratch=$(mktemp -d "$PWD/outputs/server-smoke.XXXXXX")
export COMPOSE_PROJECT_NAME="metro-smoke-$$"
export DATA_DIR="$scratch" OUTPUT_DIR="$scratch" BAG_NAME=fixture RUN_NAME=smoke
export APP_UID="$(id -u)" APP_GID="$(id -g)"
export HTTP_PORT="${SMOKE_PORT:-18080}" BIND_ADDRESS=127.0.0.1
export CONFIG_FILE=./config/mounted_lidar.json
export EXPORT_EVERY=1 PREVIEW_POINTS=1000
cleanup() { docker compose down --remove-orphans; }
trap cleanup EXIT
docker compose run --rm --entrypoint python processor scripts/create_smoke_bag.py /output/fixture
docker compose run --rm processor
docker compose up -d --wait --wait-timeout 60 web
python3 scripts/check_server_http.py "http://127.0.0.1:$HTTP_PORT"
touch "$scratch/smoke/.publishing"
python3 scripts/check_server_http.py "http://127.0.0.1:$HTTP_PORT" --not-ready
rm "$scratch/smoke/.publishing"
docker compose restart web
docker compose up -d --wait --wait-timeout 60 web
python3 scripts/check_server_http.py "http://127.0.0.1:$HTTP_PORT"
echo "Deployment smoke passed (including restart). Fixture and results: $scratch"
