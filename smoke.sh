#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/infra"

docker compose up -d --build

retries=60
sleep_interval=2
containers=$(docker compose ps -q)

while [ "$retries" -gt 0 ]; do
    all_healthy=true
    for container in $containers; do
        status=$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$container")
        if [[ "$status" == "unhealthy" || "$status" == "exited" ]]; then
            docker compose down
            exit 1
        fi
        if [[ "$status" != "healthy" ]]; then
            all_healthy=false
        fi
    done

    if [ "$all_healthy" = true ]; then
        docker compose down
        exit 0
    fi

    sleep "$sleep_interval"
    retries=$((retries - 1))
done

docker compose down
exit 1

