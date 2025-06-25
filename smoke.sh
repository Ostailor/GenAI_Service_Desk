#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")"
# Ensure Python can import the src package when running scripts directly
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

COMPOSE_FILE="infra/compose.yml"
echo "Bringing up Docker Compose stack..."
docker compose -f "$COMPOSE_FILE" up -d --build

# The llama3 model download can take several minutes.
# Increase the timeout to 5 minutes (150 retries * 2s interval) to match
# the healthcheck's start-period.
retries=150
sleep_interval=2
containers=$(docker compose -f "$COMPOSE_FILE" ps -q)

echo "Waiting for all containers to become healthy..."
while [ "$retries" -gt 0 ]; do
    all_healthy=true
    echo "--- Checking container statuses (retries left: $retries) ---"
    for container in $containers; do
        name=$(docker inspect -f '{{.Name}}' "$container" | sed 's,^/,,')
        status=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")
        echo "Container: $name, Status: $status"

        if [[ "$status" == "unhealthy" || "$status" == "exited" ]]; then
            echo "Error: Container $name is $status. Tearing down."
            docker compose -f "$COMPOSE_FILE" logs "$name"
            docker compose -f "$COMPOSE_FILE" down
            exit 1
        fi
        if [[ "$status" != "healthy" ]]; then
            all_healthy=false
        fi
    done

    if [ "$all_healthy" = true ]; then
        echo "All containers are healthy. Proceeding with migrations and tests."
        DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/postgres" \
            alembic -c alembic.ini upgrade head
        python scripts/seed_demo.py
        python scripts/db_health.py
        python scripts/load_docs.py --manifest scripts/demo_docs.json
        curl -fsS http://localhost:8000/knowledge/ready >/dev/null
        curl -fsS -X POST http://localhost:11434/api/generate \
            -d '{"model":"llama3","prompt":"ping","stream":false}' >/dev/null
        echo "Smoke test successful. Tearing down."
        docker compose -f "$COMPOSE_FILE" down
        exit 0
    fi

    echo "Not all containers are healthy yet. Retrying in $sleep_interval seconds..."
    sleep "$sleep_interval"
    retries=$((retries - 1))
done

echo "Timeout: Not all containers became healthy within the time limit. Tearing down."
docker compose -f "$COMPOSE_FILE" logs
docker compose -f "$COMPOSE_FILE" down
exit 1