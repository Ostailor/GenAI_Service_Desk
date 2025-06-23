#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/infra"

docker compose up -d --build

retries=60
sleep_interval=2

while [ "$retries" -gt 0 ]; do
    statuses=$(docker compose ps --format json | jq -r '.[].State.Health.Status')
    if echo "$statuses" | grep -q "unhealthy"; then
        docker compose down
        exit 1
    fi
    if echo "$statuses" | grep -vq "starting" && ! echo "$statuses" | grep -q "unhealthy"; then
        docker compose down
        exit 0
    fi
    sleep "$sleep_interval"
    retries=$((retries - 1))
done

docker compose down
exit 1
