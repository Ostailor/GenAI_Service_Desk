#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"
# Ensure Python can import the src package when running scripts directly
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

COMPOSE_FILE="infra/compose.yml"
docker compose -f "$COMPOSE_FILE" up -d --build

retries=60
sleep_interval=2
containers=$(docker compose -f "$COMPOSE_FILE" ps -q)

while [ "$retries" -gt 0 ]; do
    all_healthy=true
    for container in $containers; do
        status=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")
        if [[ "$status" == "unhealthy" || "$status" == "exited" ]]; then
            docker compose -f "$COMPOSE_FILE" down
            exit 1
        fi
        if [[ "$status" != "healthy" ]]; then
            all_healthy=false
        fi
    done

    if [ "$all_healthy" = true ]; then
        DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/postgres" \
            alembic -c alembic.ini upgrade head
        python scripts/seed_demo.py
        python scripts/db_health.py
        docker compose -f "$COMPOSE_FILE" down
        exit 0
    fi

    sleep "$sleep_interval"
    retries=$((retries - 1))
done

docker compose -f "$COMPOSE_FILE" down
exit 1

