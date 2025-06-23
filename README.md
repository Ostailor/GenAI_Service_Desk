# GenAI Service Desk

A reference implementation of a multi-tenant IT helpdesk powered by generative AI. This repository contains the infrastructure and application code for later phases.

## Smoke test

Use `./smoke.sh` to spin up the Docker Compose stack and verify that every
service becomes healthy. The script brings the containers up, polls their health
status via `docker inspect`, and tears the stack down when all services report
`healthy`.
